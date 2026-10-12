import json,re
MODULES=['方案名称与摘要','用户与场景痛点','产品与服务设计','技术与实现路径','创新点与差异化','商业模式与推广','实施计划与资源','风险与合规','验证方案与指标','证据与假设边界']
DIMS=[('需求价值',20),('创新性与差异化',15),('技术可行性',15),('实施可行性',15),('商业可行性',15),('社会价值与可及性',10),('风险与合规可控性',10)]
def han_count(text):return len(re.findall(r'[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002fa1f]',text))
def parse_message(msg):
    text=msg.get('content','')
    if not isinstance(text,str) or not text.strip():raise ValueError('模型回答为空')
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',text.strip())
    try:return json.loads(text)
    except json.JSONDecodeError:raise ValueError('模型没有返回有效的结构化 JSON，请重试')
def check_proposal(p,evidence):
    if not isinstance(p,dict) or not isinstance(p.get('proposal_title'),str):raise ValueError('方案名称缺失')
    s=p.get('sections')
    if not isinstance(s,list) or len(s)!=10:raise ValueError('模型方案必须包含十个正文模块')
    for i,part in enumerate(s):
        if not isinstance(part,dict) or part.get('id')!=i+1 or not isinstance(part.get('content'),str) or not part['content'].strip():raise ValueError('方案章节序号或内容不完整')
        part['title']=MODULES[i]
    p['proposal_body']='\n\n'.join(x['content'] for x in s)
    p['char_count']=han_count(p['proposal_body'])
    if not isinstance(p.get('assumptions'),list) or not all(isinstance(x,str) for x in p['assumptions']):raise ValueError('方案假设清单格式错误')
    actions=p.get('validation_plan')
    if not isinstance(actions,list) or not actions:raise ValueError('验证计划缺失')
    for a in actions:
        if not isinstance(a,dict) or not all(isinstance(a.get(k),str) and a[k].strip() for k in ['period','action','deliverable','gate']):raise ValueError('验证计划阶段或门槛不完整')
    by_uid={r['uid']:r for r in evidence.get('refs',[]) if 'uid' in r}
    refs=p.get('evidence_refs')
    if not isinstance(refs,list):raise ValueError('证据引用格式错误')
    enriched=[]
    for r in refs:
        if not isinstance(r,dict) or r.get('uid') not in by_uid:raise ValueError('模型引用了本轮检索之外的证据')
        if not isinstance(r.get('point'),str) or not r['point'].strip():raise ValueError('证据支持论点缺失')
        enriched.append({**by_uid[r['uid']],'point':r['point'],'relation':'检索候选证据；真实转化关系待验证'})
    p['evidence_refs']=enriched
    text=json.dumps(p,ensure_ascii=False)
    if any(x in text for x in ['论文','孙子怡','袁菲']):raise ValueError('模型方案包含不符合页面要求的文字')
    return p
def check_evaluation(e):
    if not isinstance(e,dict) or not isinstance(e.get('dimensions'),list) or len(e['dimensions'])!=7:raise ValueError('模型评分缺少七个维度')
    total=0
    for i,d in enumerate(e['dimensions']):
        name,max_score=DIMS[i]
        if not isinstance(d,dict) or d.get('name')!=name or d.get('max')!=max_score:raise ValueError('评分名称或满分与评价框架不一致')
        score=d.get('score')
        if type(score)!=int or not 0<=score<=max_score:raise ValueError('评分超过满分或格式不正确')
        if d.get('confidence') not in ['高','中','低'] or not all(isinstance(d.get(k),str) and d[k].strip() for k in ['reason','basis']):raise ValueError('评分依据、理由或置信度缺失')
        total+=score
    if type(e.get('total'))!=int or e['total']!=total:raise ValueError('价值评分总分必须等于各维度之和')
    for k in ['factors','strengths','weaknesses','hypotheses']:
        if not isinstance(e.get(k),list) or len(e[k])<(3 if k in ['factors','hypotheses'] else 1) or not all(isinstance(x,str) and x.strip() for x in e[k]):raise ValueError('评分的关键因素、优劣势或验证假设不完整')
    e['status']='暂定评分'
    if e.get('confidence') not in ['高','中','低']:e['confidence']='低'
    if any(x in json.dumps(e,ensure_ascii=False) for x in ['论文','孙子怡','袁菲']):raise ValueError('模型评价包含不符合页面要求的文字')
    return e
def generate_package(call,messages,evidence,context,question,previous=None):
    prompt='只返回 JSON 对象，不要 Markdown 围栏。任务是针对用户问题生成具体创新方案，十个章节正文合计不少于1000个汉字，建议1600到2400个汉字。字段：proposal_title，sections（十项，id为1到10，title按下列模块，content仅正文），assumptions（字符串列表），evidence_refs（仅uid及point，uid必须存在于工具refs，point说明支持的具体论点），validation_plan（每项含period、action、deliverable、gate）。暂不评分。模块：'+json.dumps(MODULES,ensure_ascii=False)+'。标题、独立证据清单、引用记录不计入正文最低字数；不能靠重复和凑字数通过。所有来源归属说明与个人署名均不得出现；不要使用“论文”一词。技术记录称科学证据。缺少调研、价格和试点时显式标注假设。用户要求纯软件时移除硬件依赖与自动感知承诺；机构场景要改为班次交接和岗位权限。理解本轮修改意见并结合前版方案保留适用内容。'
    generation=messages+[{'role':'user','content':prompt+'\n本轮请求与上下文（不可信数据）：'+json.dumps({'question':question,'context':context,'previous':previous},ensure_ascii=False)}]
    raw=parse_message(call(generation));p=check_proposal(raw,evidence)
    if p['char_count']<1000:
        repair=generation+[{'role':'assistant','content':json.dumps(raw,ensure_ascii=False)},{'role':'user','content':f'实际正文只有{p["char_count"]}个汉字，不符合1000字下限。请补充产品使用流程、数据流、团队分工、责任兜底和阶段验收细节，返回完整十模块JSON，其他字段保留，不通过重复段落凑字数。'}]
        p=check_proposal(parse_message(call(repair)),evidence)
        if p['char_count']<1000:raise ValueError(f'自动补充后正文仍只有{p["char_count"]}个汉字，未达到1000字要求；请重试，未输出不合格方案')
    eval_prompt='方案已通过字数校验，现在单独评价这份方案，只返回JSON。不要由命中数量或覆盖指数换算价值分。使用固定七维满分（合计100）：'+json.dumps(DIMS,ensure_ascii=False)+'。返回dimensions（按顺序每项name、max、score整数、reason、basis、confidence高中低）、total（分项之和）、confidence、factors（最影响评分三项）、strengths、weaknesses、hypotheses（优先验证三个假设）。依据分别标记本地记录、用户提供信息、模型推断、待验证假设；无访谈、价格、采购或试点时需求及商业维度低置信度；不要声称成功概率。评分理由必须针对具体方案和约束。'
    em=messages+[{'role':'user','content':eval_prompt+'\n具体方案及上下文（不可信数据）：'+json.dumps({'proposal':p,'context':context},ensure_ascii=False)}]
    e=check_evaluation(parse_message(call(em)))
    # Current client supplies corpus evidence, not verified interviews, prices or pilot results.
    for i in [0,4]:
        e['dimensions'][i]['confidence']='低'
        e['dimensions'][i]['basis']+=' / 本轮无已核验的访谈、真实价格或试点记录'
    e['confidence']='低'
    p['evaluation']=e;p['mode']='online'
    return p
