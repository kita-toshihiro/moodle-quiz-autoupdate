# A module file that collects functions to be called
# License: CC BY-SA https://creativecommons.org/licenses/by-sa/4.0/ , Copyright: KITA Toshihiro https://tkita.net/

MOODLE_DIR = '/var/www/html/moodle'

def shcmd(command_str, cwd=MOODLE_DIR):
    # If cwd is specified, the command will be executed in that directory.
    import subprocess
    import shlex

    command_list = shlex.split(command_str)
    result = subprocess.run(
        command_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
        cwd=cwd
    )
    return result.stdout.strip()


def get_courseid(out):
    import re
    match = re.search(r"Added course \w+ with id: (\d+)", out)
    if match:
        courseid = int(match.group(1))
        return courseid
    else:
        return -1


'''
moosh -n gradeitem-list courseid=%d : 
"id","courseid","categoryid","itemname","itemtype","itemmodule","iteminstance","itemnumber","iteminfo","idnumber","calculation","gradetype","grademax","grademin","scaleid","outcomeid","gradepass","multfactor","plusfactor","aggregationcoef","aggregationcoef2","sortorder","display","decimals","hidden","locked","locktime","needsupdate","weightoverride","timecreated","timemodified"
"393","59","Top","","course","","57","","","","","1","100.00000","0.00000","","","0.00000","1.00000","0.00000","0.00000","0.00000","1","0","","0","0","0","0","0","1744899583","1744899583"
"395","59","Top/?","Quiz s1","mod","quiz","213","0","","","","1","100.00000","0.00000","","","0.00000","1.00000","0.00000","0.00000","0.00000","3","0","","0","0","0","0","0","1744899861","1744899861"
"396","59","Top/?","Quiz s2","mod","quiz","214","0","","","","1","100.00000","0.00000","","","0.00000","1.00000","0.00000","0.00000","0.00000","4","0","","0","0","0","0","0","1744906772","1744906781"
'''
import csv
import io
from typing import List
def get_quizids(out: str, str_new) -> List[int]:
    quizids = []
    f = io.StringIO(out)
    reader = csv.DictReader(f)
    for row in reader:
        if (row['itemmodule'] == 'quiz') and (str_new not in row['itemname']):
            quizids.append(int(row['id']))
    return quizids


'''
名,姓,IDナンバ,所属組織,部署,メールアドレス,"小テスト:Quiz s1 (実データ)",このコースからの最新ダウンロード日時
anonfirstname1,anonlastname1,,,,anon1@doesntexist.com,10,1744907992
anonfirstname2,anonlastname2,,,,anon2@doesntexist.com,25,1744907992
anonfirstname3,anonlastname3,,,,anon3@doesntexist.com,78,1744907992
'''
# Returns a dict such that res['anon1@doesntexist.com'] = 10
import csv
import io
import re
def get_quiz_score(out: str) -> dict:
    res = {}
    reader = csv.DictReader(io.StringIO(out))
    # First, find the score column name in the header
    quiz_field = None
    for field in reader.fieldnames:
        if field and re.match(r'^小テスト:.*\(実データ\)$', field):
            quiz_field = field
            break
    
    if not quiz_field:
        raise ValueError("Score column not found.")
    
    for row in reader:
        email = row.get('メールアドレス')
        score = row.get(quiz_field)
        if email and score:
            try:
                res[email] = int(float(score))
            except ValueError:
                pass  # Skip if score is not an integer
    return res


def calculate_average_score(res: dict) -> float:
    if not res:
        return 0.0
    total_score = sum(res.values())
    count = len(res)
    average = total_score / count
    return average


def top_score(res: dict) -> float:
    if not res:
        return 0.0
    return max(res.values())


def quiz_result_comment(qscore: int) -> str:
    max_questions = 4
    """
    Analyzes the quiz score assuming it represents bit flags for correct answers.
    Assumes bit 0 corresponds to Question 1, bit 1 to Question 2, etc.
    Returns:
        A list of integers representing the 1-based index of incorrectly answered questions.
    """
    incorrect_questions = []
    for i in range(max_questions):
        # Check the i-th bit. If it's 0, the question was incorrect.
        if not (qscore >> i) & 1:
            incorrect_questions.append(i + 1) # Append 1-based question number
    # incorrect_questions should be like [1, 3, 8]

    num_incorrect = len(incorrect_questions)

    if num_incorrect == 0:
        return "Perfect."
    elif num_incorrect == 1:
        question_part = f"Question No.{incorrect_questions[0]}"
        verb = "is"
    else:
        formatted_numbers = [f"Question No.{num}" for num in incorrect_questions]
        question_part = ", ".join(formatted_numbers)
        verb = "are"

    feedback_message = f"{question_part} {verb} incorrect. More basic questions related to those questions should be generated."
    return feedback_message


def sectionid_from_quizid(quizid: int, courseid: int) -> int:
    """
    Retrieves the section ID associated with a quiz grade item ID.
    It fetches the grade item list for the course, finds the item by ID,
    and parses the section number from its name (assuming format like "Quiz sX").
    Args:
        quizid: The ID of the grade item (e.g., 395).
        courseid: The ID of the course containing the quiz.
    Returns:
        The parsed section ID (e.g., 1), or -1 if not found or name format is wrong.
    """
    try:
        out = shcmd(f'moosh -n gradeitem-list courseid={courseid}')
        f = io.StringIO(out)
        reader = csv.DictReader(f)
        for row in reader:
            if row['id'] == str(quizid) and row['itemmodule'] == 'quiz':
                itemname = row['itemname']
                # Try to extract section number from name like "Quiz s1", "Quiz s2" etc.
                match = re.search(r'[Ss](\d+)', itemname)
                if match:
                    return int(match.group(1))
                else:
                    print(f"Warning: Could not parse section ID from itemname '{itemname}' for quizid {quizid}")
                    return -1 # Indicate failure to parse section ID
    except Exception as e:
        print(f"Error getting section ID for quizid {quizid} in course {courseid}: {e}")
        return -1 # Indicate error

    return -1 # Indicate quizid not found


def create_question_xml(eval_comment: str) -> str:
    from openai import OpenAI
    import tempfile

    with open("../keys/openai-key.txt", "r") as file:
        client = OpenAI(api_key=file.read().strip())
    #model = "gpt-4o"
    model = "gpt-4o-mini"
    xmlfile0 = 'moodle-quest1.xml'
    with open(xmlfile0, 'r') as ff:
        xml0 = ff.read()
    #print(xml0)
    prompt1 = f'''
    You are an online quiz developer.
    Please create 4 4-choice questions in XML format.
    Please also indicate the correct answer. Please use MathJax format in writing formulae.
    {eval_comment}
    {xml0}
    '''
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt1}]
    )
    res1 = response.choices[0].message.content.strip()
    #print(res1)

    prompt2 = '''
    Please correct the output as below.
    * Delete the option number
    * Delete option letters (a, b, c, etc.)
    * Correct answer options have a score of 100.
    * The question name (between <name><text> and </text></name>) is \
    a summary of the question text in about 5 words, \
    and at the beginning it has the question number like No.1, No.2, No.3, ...
    * For each question, write one "general feedback" of about 50 words \
    after </questiontext> surrounded by <generalfeedback><text> and </text></generalfeedback>
    * "General feedback" includes links such as reference Wikipedia pages \
    with target=_BLANK specified.
    * Write <shuffleanswers>true</shuffleanswers> for each question
    * <defaultgrade> value must be doubled step by step for each question like 1.0, 2.0, 4,0, 8.0, ...
    * Make sure ]]> is not missing corresponding to each <![CDATA[
    '''[1:]

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": 'You are an AI that must respond only in valid XML format. Do not add any explanations, markdown syntax (like ```xml), or additional text. Output a well-formed XML document, starting with <quiz>.'},
            {"role": "user", "content": prompt1},
            {"role": "assistant", "content": res1},
            {"role": "user", "content": prompt2},
        ],
    )
    res2 = response.choices[0].message.content.strip()
    res2 = res2.replace("```xml", '').replace("```", '')
    #print(res2)
    fd, temp_xml_path = tempfile.mkstemp(suffix='.xml', text=True)
    with open(fd, 'w', encoding='utf-8') as f:
        f.write(res2)

    return temp_xml_path


