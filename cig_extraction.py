#--coding:utf-8--
import os
import sys
import shutil
from mako.template import Template
import re
import copy

#吸烟状况代码(n=1,2,3,4)与DisplayName的对应
SmokingStatus=[u'现在每天吸',u'现在吸,但不每天吸',u'过去吸,现在不吸',u'从不吸']
#单位转换为对应英文单词,便于扩展新的表达方式
unit={u'年':'year',u'月':'month',u'日':'day',u'天':'day',u'周':'week',u'支':'piece',u'根':'piece',u'包':'package'}
#中文数字转换阿拉伯数字对照表
ChiNum={u'半':'.5',u'一':'1',u'二':'2',u'两':'2',u'三':'3',u'四':'4',u'五':'5',u'六':'6',u'七':'7',u'八':'8',u'九':'9',u'十':'10'}

def DigitCorrect(a):
#中文数字直接转换为对应阿拉伯数字后,两位数会被错误"翻译",通过这一函数加以修正
    if '.' in a:
        b = a[0 : a.find('.')]
        c = a[a.find('.') : ]
    else:
        b = a
        c = ''
    if len(b)>2:
        if "10" in b:
            b = b.split('10')
            if b[0]=='':
                b[0]=1
            else:
                b[0]=int(b[0])
            if b[1] == '':
                b[1] = 0
            b = b[0]*10 + int(b[1])
    elif b == '':
        b = 0
    else: 
        b = int(b)
    a = str(b)+c
    return a.encode('utf8')
        
def out2Mako(self):
    '''
    #利用Mako文件将抽提信息格式化输出
    #print PiecePerDay
    xmlContent = Template(filename="smokingCDAEntry_shi.mako").render(FilePathName=locals()['self.InputFileName'], LineNumber=locals()['self.LineNumber'], SmkStaCode=locals()['self.SmkStaCode'], SmkStaDisName=locals()['self.SmkStaDisName'], text=locals()['text'], PiecePerDay=locals()['self.PiecePerDay'], =locals()['self.SmkPeriod'])
    OutFileName=self.RltsDir+self.InputFileName.split('.')[0]+"#"+str(self.LineNumber)+".xml"
    outfile=open(OutFileName, "w")
    outfile.write(xmlContent.encode('utf8'))
    outfile.close()
    '''
    pass
    
def ieRlts_log(outpath):
    #record the extracted information for future evaluation
    if not os.path.isfile(outpath):
        ExtractedInf_file = open(outpath, 'w')
    else:
        ExtractedInf_file = open(outpath, "a")
    header = u"ID\t吸烟状况代码\t吸烟时长(年)\t日吸烟量(支)\t近1年内是否吸烟\n"
    ExtractedInf_file.write(header.encode('utf8'))
    return ExtractedInf_file

def validityDetector(uniCodeText):
    neg_patterns = [u'忌.{,5}烟', u'烟肼']   #<禁忌吸烟>的情况不认为是吸烟史描述;含有“烟”字的药物名称也排除
    new_str = uniCodeText
    for np in neg_patterns:
        for m in re.compile(np).findall(new_str):
            new_str = new_str.replace(m, '#' * len(m))
    if u'烟' in new_str:
        return 1, new_str
    else:
        return 0
    
def smkDenyDetector(uniCodeText):
    #<[否认无不]...[抽吸]烟>
    xxs=[u'否认.{0,5}[抽吸]烟', u'[无不].{0,5}[抽吸]烟', u'[无不].{0,5}烟酒']
    for xx in xxs:
        if re.compile(xx).findall(uniCodeText):
            return 1
    return 0
    
def spliter(uniCodeText):
    sentenceList = uniCodeText.split(u'。')
    return sentenceList

def findScope(text, start, end, left, right):   #返回特定位置左右一定范围的上下文内容
    return text[max(0, start - left) : min(len(text), end + right)]

def durationExtractor(uniCodeText):
    numRe_day = None
    for durationRe in re.compile(u'[0-9\.半一二两三四五六七八九十数][0-9\.半一二两三四五六七八九十数]*[余多数个+]?[天日周年月]').findall(uniCodeText):
        p = re.compile(u'[0-9\.半一二两三四五六七八九十数][0-9\.半一二两三四五六七八九十]*[余多数个+]?')
        numRe = p.findall(durationRe)[0]
        numRe = numRe.replace(u'+','').replace(u'余','').replace(u'多','').replace(u'个','')   #去掉"余多数+"
        numRe = numRe.replace(u'数', u'五')    #数月、数年等近似为5
        #中文数字转化为文本型数字
        for i in ChiNum.keys():
            numRe = numRe.replace(i, ChiNum[i])
        numRe = DigitCorrect(numRe)
        #提取单位<[天日周年月]>
        unitRe = unit[re.compile(u'[天日周年月]').findall(durationRe)[0]]
        if unitRe == 'year':
            numRe_day = float(numRe) * 365
        elif unitRe == 'month':
            numRe_day = float(numRe) * 30
        elif unitRe == 'day':
            numRe_day = float(numRe)
    return numRe_day
    
def quitDetector(uniCodeText):  #戒烟信息
    quit_flag = 0
    SmkInThisYear = None
    quit_patterns = [u'已戒烟([0-9\.半一二两三四五六七八九十数][0-9\.半一二两三四五六七八九十数]*[余多数个+]?[天日周年月])', u'戒烟([0-9\.半一二两三四五六七八九十数][0-9\.半一二两三四五六七八九十数]*[余多数个+]?[天日周年月])', u'烟.{,10}[^\d]([0-9\.半一二两三四五六七八九十数][0-9\.半一二两三四五六七八九十数]*[余多数个+]?[天日周年月])[^\d，。]{,3}戒', u'已戒烟', u'烟.{,10}戒', u'戒烟']
    for qp in quit_patterns:
        for m in re.compile(qp).findall(uniCodeText):
            quit_flag = 1
            quit_duration_day = durationExtractor(m)
            if quit_duration_day is None:   #没有戒烟时长信息
                SmkInThisYear = None
            elif quit_duration_day >= 365:
                SmkInThisYear = 0
            else:
                SmkInThisYear = 1
            break
        if quit_flag:
            break
    return quit_flag, SmkInThisYear
            
def smkHistDetector(uniCodeText):   #吸烟时长（年）
    smkHist_mention = None
    smkHist_year = None
    smkHist_patterns = [u'[^戒\d]{,3}烟[^戒\d]{,5}[0-9\.半一二两三四五六七八九十][0-9\.半一二两三四五六七八九十]*[余数多+]?[天日周年月]', u'[0-9\.半一二两三四五六七八九十][0-9\.半一二两三四五六七八九十]*[余数多+]?[天日周年月][^戒]{,5}烟史', u'[[支包根][^每1一/／\d][0-9\.半一二两三四五六七八九十][0-9\.半一二两三四五六七八九十]*[余数多+]?[天日周年月]']
    for hisp in smkHist_patterns:
        for smkHist in re.compile(hisp).findall(uniCodeText):
            smkHist_mention = 1
            smkHist_day = durationExtractor(smkHist)
            if smkHist_day is None:
                smkHist_year = None
            else:
                smkHist_year = smkHist_day / 365
            #print smkHist_patterns.index(hisp)
            break
        if smkHist_mention == 1:
            break
    return smkHist_mention, smkHist_year
            
def smkQuantDetector(uniCodeText):
    smkQuant_mention = None
    smk_daily = None
    smkQuant_piece = None
    smkQuant_num = None
    smkQuant_piece_day = None
    smkQuant_time_unit = None   #吸烟量表述中不以“天”为单位的，视为“现在吸，但不是每天吸”
    smkQuant_patterns = [u'烟.{,5}[^\d]([每0-9\.半一二两三四五六七八九十数]+[天日周年月][^\d，。]{,3}[0-9\.半一二两三四五六七八九十数][0-9\./／半一二两三四五六七八九十数]*[余多半+]?[支包根])', u'烟.{,5}[^\d]([0-9\.半一二两三四五六七八九十数][0-9\./／半一二两三四五六七八九十数]*[余多半+]?[支包根][余多半+]?[1每一/／][0-9]*[天日周年月]?)', u'[每0-9\.半一二两三四五六七八九十数]+[天日周年月][^\d]{,3}烟[^\d]{,6}[0-9\.半一二两三四五六七八九十数][0-9\./／半一二两三四五六七八九十数]*[余多半+]?[支包根][-~至～－][0-9\.半一二两三四五六七八九十数][0-9\./／半一二两三四五六七八九十数]*[余多半+]?[支包根]',  u'[每0-9\.半一二两三四五六七八九十数]+[天日周年月][^\d，。]{,3}烟[^\d]{,6}[0-9\.半一二两三四五六七八九十数][0-9\./／半一二两三四五六七八九十数]*[余多半+]?[支包根]', u'日[抽吸]烟[^\d]{,6}[0-9\.半一二两三四五六七八九十数][0-9\./／半一二两三四五六七八九十数]*[余多半+]?[支包根]']
    for smkqp in smkQuant_patterns:
        for m in re.compile(smkqp).findall(uniCodeText):
            smkQuant_mention = 1
            #print smkQuant_patterns.index(smkqp)
            #print m.encode('utf8')
            m_rmVag = m.replace(u'+','').replace(u'余','').replace(u'多','') #去掉模糊信息
            m_exactValue = m_rmVag.replace(u'数',u'五').replace(u'每',u'一') #数包、数支等近似为5
            for i in ChiNum.keys():
                m_exactValue = m_exactValue.replace(i,ChiNum[i])    #将中文数字先转换为阿拉伯数字,此时2位数会被错误"翻译",进一步处理是通过DigitCorrect函数加以修正
            if re.compile(u'[1-9][/／][1-9]').findall(m_exactValue):  #对于分数的情况，做除法
                x, y = re.compile(u'(\d+)[/／](\d+)').findall(m_exactValue)[0]
                smkQuant_num = round(float(x)/float(y), 2)
            if re.compile(u'[0-9][0-9]*[-~至～－][0-9][0-9]*').findall(m_exactValue):   #对于数值为“x～y”或“x至y”或"x-y"的，取x与y的平均值
                x, y = re.compile(u'(\d+)[-~至～－](\d+)')[0]
                smkQuant_num = round((float(x) + float(y))/2, 2)
            if smkQuant_num is None:
                smkQuant_num = DigitCorrect(re.compile(u'([0-9\.]?[0-9]+)[支包根]').findall(m_exactValue)[0])
            smkQuant_unit = unit[re.compile(u'[支包根]').findall(uniCodeText)[0]]  #提取单位，进行换算
            if smkQuant_unit == 'piece':
                smkQuant_piece = float(smkQuant_num)
            elif smkQuant_unit == 'package':
                smkQuant_piece = float(smkQuant_num) * 20
            if re.compile(u'[0-9\.半一二两三四五六七八九十/／]+[天日周年月]').findall(m_exactValue):    #提取抽烟量时间单位
                if re.compile(u'[/／][0-9\.半一二两三四五六七八九十]*[天日周年月]').findall(m_exactValue):   #m_exactValue中“每”已变为“一”
                    smk_freq, smk_freq_unit = re.compile(u'[/／]([0-9\.半一二两三四五六七八九十]*)([天日周年月])').findall(m_exactValue)[0]
                    if smk_freq == u'':
                        smk_freq = u'1'
                else:
                    smk_freq, smk_freq_unit = re.compile(u'([0-9\.半一二两三四五六七八九十数]+)([天日周年月])').findall(m_exactValue)[0]
                
                for i in ChiNum.keys():
                    smk_freq = DigitCorrect(smk_freq.replace(i,ChiNum[i]))   #将中文数字先转换为阿拉伯数字,此时2位数会被错误"翻译",通过DigitCorrect函数加以修正
                
                #乱码可能导致抽出的数字为0，导致除零错误
                if smk_freq > 0:
                    if unit[smk_freq_unit] == 'day':
                        smkQuant_piece_day = round(smkQuant_piece/float(smk_freq), 2)
                        smk_daily = 1                    
                    elif unit[smk_freq_unit] == 'week':
                        smkQuant_piece_day = round(smkQuant_piece/(float(smk_freq) * 7), 2)
                        smk_daily = 0
                    elif unit[smk_freq_unit] == 'month':
                        smkQuant_piece_day = round(smkQuant_piece/(float(smk_freq) * 30), 2)
                        smk_daily = 0
                    elif unit[smk_freq_unit] == 'year':
                        smkQuant_piece_day = round(smkQuant_piece/(float(smk_freq) * 365), 2)
                        smk_daily = 0
                    else:
                        print 195, 'something wrong!!!'
                else:
                    print 206
                    print '[Error] smoking frequency is zero'
                    smkQuant_piece_day = None
                    smk_daily = None
            #handle the simple expression of smoking frequency
            elif re.compile(u'日[吸抽]烟[^\d]{,6}' + smkQuant_num + u'[支包根]').findall(m_exactValue):
                smk_freq = u'1'
                smkQuant_piece_day = round(smkQuant_piece/float(smk_freq), 2)
                smk_daily = 1
            break
        if smkQuant_mention:
            break
    return smkQuant_piece_day, smk_daily
                
def logicCombine(quit_flg, quit_lessOneYear, smkHist_mention, smkHist_year, smkQuant_piece_day, smk_daily):
    results = dict.fromkeys(['SmkStaCode', 'SmkStaDisName', 'PiecePerDay_num', 'SmkPeriod_year', 'SmkInThisYear'])
    if quit_flg:
        results['SmkStaCode'] = '3'
        results['SmkStaDisName'] = u'过去吸,现在不吸'
        if quit_lessOneYear is None:
            results['SmkInThisYear'] = None
        elif quit_lessOneYear == 1:
            results['SmkInThisYear'] = u'True'
        elif quit_lessOneYear == 0:
            results['SmkInThisYear'] = u'False'
    else:
        results['SmkInThisYear'] = u'True'   #未戒烟的，默认最近一年吸烟
        if smk_daily is None or smk_daily == 1:   #没有具体日吸烟量信息的，默认是每天吸烟
            results['SmkStaCode'] = '1'
            results['SmkStaDisName'] = u'现在每天吸'
        elif smk_daily == 0:
            results['SmkStaCode'] = '2'
            results['SmkStaDisName'] = u'现在吸,但不每天吸'
    if smkQuant_piece_day is None:  #日吸烟量，不论是否已戒烟，都可能有该信息
        results['PiecePerDay_num'] = None
    else:
        results['PiecePerDay_num'] = str(smkQuant_piece_day)
    if smkHist_year is None:    #吸烟时长，不论是否已戒烟，都可能有该信息
        results['SmkPeriod_year'] = None
    else:
        results['SmkPeriod_year'] = str(smkHist_year)
    return copy.deepcopy(results)
            
def process_oneReport(uniCodeText, ieRlt_out_path = None):  #process a paragraph, maybe the content of one report
    uniCodeRlts = dict.fromkeys(['SmkStaCode', 'SmkStaDisName', 'PiecePerDay_num', 'SmkPeriod_year', 'SmkInThisYear'])
    denySmk_flag = smkDenyDetector(uniCodeText)
    if ieRlt_out_path is None:
        toLog = False
    else:
        toLog = True
    if denySmk_flag == 1:   #出现否认吸烟的，直接输出，不再进行后续的处理
        uniCodeRlts['SmkStaCode'] = '4'
        uniCodeRlts['SmkStaDisName'] = u'从来不吸'
        uniCodeRlts['SmkInThisYear'] = u'False'
        if toLog:
            ExtractedInf_file = ieRlts_log(ieRlt_out_path, uniCodeRlts)
        return copy.deepcopy(uniCodeRlts)
    
    sentStart = 0
    for uniSentence in spliter(uniCodeText):  #split the sencences
        valid_rlt = validityDetector(uniSentence)   #去除掉invalid的“烟”字
        if valid_rlt == 0:  #当前句子没有吸烟相关的信息
            continue
        sent_valid = valid_rlt[1]   #含有吸烟信息的句子
        quit_flg, quit_lessOneYear = quitDetector(sent_valid)    #是否提及戒烟，一年内是否吸烟
        
        smkHist_mention, smkHist_year = smkHistDetector(uniCodeText) #吸烟时长（年）信息
        smkQuant_piece_day, smk_daily = smkQuantDetector(uniCodeText)   #日吸烟量及是否每天吸烟
        
        sentStart += len(uniSentence)
        
    #对于未否认吸烟的患者进行逻辑判断
    uniCodeRlts = logicCombine(quit_flg, quit_lessOneYear, smkHist_mention, smkHist_year, smkQuant_piece_day, smk_daily)
    
    if toLog:
        ExtractedInf_file = ieRlts_log(ieRlt_out_path, uniCodeRlts)
    return uniCodeRlts

if  __name__ == '__main__':
    fin = open('example.txt', 'r')
    content = ''.join(fin.readlines())
    fin.close()
    
    
    data = process_oneReport(content.decode('utf8'))
    fout = open('result.txt', 'w')
    for k in data.keys():
        if data[k] is None:
            fout.write(k.encode('utf8') + '\tNA\n')
        else:
            fout.write(k.encode('utf8') + '\t' + data[k].encode('utf8') + '\n')
    fout.close()
            
    # example = u'吸烟史10年，平均20支/日，戒烟2年。'
    # print process_oneReport(example)
            
        
        
