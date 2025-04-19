# Run this script once at the beginning
# License: Public domain, Copyright: KITA Toshihiro https://tkita.net/

import adaptive_quiz_moosh_mod1 as mm

numsection = 3

## Create a new Moodle course
out = mm.shcmd('moosh -n course-create --format topics --numsections %d --fullname "Demo Course 1" demo1' % numsection)
courseid = mm.get_courseid(out)

## Create quizzes for each participant (or you can manually create quizzes)
questionxmlfile = '/root/iclea2025/moodle-quest1.xml'
for i in range(1,numsection+1):
    out = mm.shcmd('moosh -n activity-add --name "Quiz s%d" --section %d quiz %d' % (i, i, courseid))
    quizid = int(out)
    print(f"Quiz id {quizid}")
    out = mm.shcmd('moosh -n question-import %s %d' % (questionxmlfile, quizid))
    print(out)

# Save the parameter values
import json
params = {
    "numsection": numsection,
    "courseid": courseid
}
with open('params.json', 'w', encoding='utf-8') as f:
    json.dump(params, f, indent=4, ensure_ascii=False)

