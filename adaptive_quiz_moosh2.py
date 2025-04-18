# If you run this script once a day using cron, it will generate new quizzes for each section (i.e. each learner) based on their daily quiz results.
# License: Public domain, Copyright: KITA Toshihiro https://tkita.net/

import adaptive_quiz_moosh_mod1 as mm
import json
from datetime import datetime

# load parameter values
with open('params.json', 'r', encoding='utf-8') as f:
    params = json.load(f)

numsection = params['numsection']
courseid =   params['courseid']
print(numsection)
print(courseid)

# get Quiz ids
out = mm.shcmd('moosh -n gradeitem-list courseid=%d' % courseid)
quizids = mm.get_quizids(out, "suppl")
print(quizids)

# get score of each quiz and create new quiz based on the score
for quizid in quizids:
    out = mm.shcmd('moosh -n gradebook-export %d %d' % (quizid, courseid))
    qscores = mm.get_quiz_score(out)
    qscore = mm.top_score(qscores)
    # qscore = mm.calculate_average_score(qscores)
    print(qscore)
    # comments that tells which question was answered correctly (qscore indicates bit flags)
    eval_comment = mm.quiz_result_comment(int(qscore))
    print(eval_comment)
    #
    # create new quiz based on the comments for each learner (in each section)
    questionxmlfile = mm.create_question_xml(eval_comment)
    sectionid = mm.sectionid_from_quizid(quizid, courseid)
    print(sectionid)
    datestr = datetime.now().strftime("%Y_%m%d")
    out = mm.shcmd('moosh -n activity-add --name "Quiz s%d(%s)suppl" --section %d quiz %d' % (sectionid, datestr, sectionid, courseid))
    quizid_new = int(out)
    out = mm.shcmd('moosh -n question-import %s %d' % (questionxmlfile, quizid_new))
    

