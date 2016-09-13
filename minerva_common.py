import credentials_local
import requests,sys
import datetime
from datetime import datetime as dt

cookie_data = {}
referer = ""
s = requests.Session()

def minerva_get(func):
	sys.stderr.write("? " + func + "\n")
	global referer
	url = "https://horizon.mcgill.ca/pban1/" + func
	r = s.get(url,cookies = cookie_data, headers={'Referer': referer})
	referer = url
	return r

def minerva_post(func,req):
	sys.stderr.write("> " + func + "\n")
	global referer
	url = "https://horizon.mcgill.ca/pban1/" + func
	r = s.post(url,data = req,cookies = cookie_data,headers = {'Referer': referer})
	referer = url
	return r

def minerva_login():
	minerva_get("twbkwbis.P_WWWLogin")
	minerva_post("twbkwbis.P_ValLogin",{'sid': credentials_local.id, 'PIN': credentials_local.pin})
	r = minerva_get("twbkwbis.P_GenMenu?name=bmenu.P_MainMnu")
	minerva_get('twbkwbis.P_GenMenu?name=bmenu.P_RegMnu&param_name=SRCH_MODE&param_val=NON_NT')


class MinervaState:
        register,wait,closed,possible,unknown,wait_places_remaining,full,full_places_remaining,only_waitlist_known = range(9)
class MinervaError:
	reg_ok,reg_fail,reg_wait,course_none,course_not_found,user_error,net_error,require_unsatisfiable = range(8)


def get_term_code(term):
	part_codes = {'FALL': '09', 'FALL-SUP': '10', 'WINTER': '01', 'WINTER-SUP': '02', 'SUMMER': '05', 'SUMMER-SUP': '06'}
	if term == "PREVIOUSEDUCATION":
		return '000000' # Sort first
	elif term.isdigit(): # Term code
		return term
	elif term[0].isdigit(): #Year first
		year = term[0:4]
		if term[4] == '-':
			part = term[5:]
		else:
			part = term[4:]
		part = part_codes[part.upper()]

	else:
		year = term[-4:]
		if term[-5] == '-':
			part = term[:-5]
		else:
			part = term[:-4]
		
		part = part_codes[part.upper()]

	return year + part

def get_status_code(status,short = False):
	if short:
		status_codes = {'Registered': 'R','Web Registered': 'R','(Add(ed) to Waitlist)': 'W', 'Web Drop': 'DROP'}
	else:
		status_codes = {'Registered': 'R','Web Registered': 'RW','(Add(ed) to Waitlist)': 'LW', 'Web Drop': 'DW'}

	return status_codes[status]

def get_type_abbrev(type):
	types = {'Lecture': 'Lec','Tutorial': 'Tut','Conference': 'Conf','Seminar': 'Sem','Laboratory': 'Lab','Student Services Prep Activity': 'StudSrvcs'}
	if type in types:
		return types[type]
	else:
		return type

# Doesn't really do much. Just tries a few tricks to shorten the names of buildings
def get_bldg_abbrev(location):
	subs = {'Building': '', 'Hall': '', 'Pavillion': '','Biology': 'Bio.','Chemistry': 'Chem.','Physics': 'Phys.', 'Engineering': 'Eng.','Anatomy': 'Anat.', 'Dentistry': 'Dent.','Medical': 'Med.', 'Life Sciences': 'Life. Sc.'}
	for sub in subs:
		location = location.replace(sub,subs[sub])

	return location

def get_minerva_weekdays(weekend = False):
	if weekend:
		return ['M','T','W','R','F','S','U']
	else:
		return ['M','T','W','R','F']

def get_real_weekday(minerva_day):
	return get_real_weekday.map[minerva_day]
get_real_weekday.map = {'M': 'Monday','T':'Tuesday','W': 'Wednesday','R': 'Thursday','F': 'Friday','S': 'Saturday','U': 'Sunday'}

def get_ics_weekday(minerva_day):
	return {'M': 'MO','T': 'TU','W': 'WE','R': 'TH','F': 'FR','S': 'SA', 'U': 'SU'}[minerva_day]

def minervac_sanitize(text):
	return text.encode('ascii','ignore')

def get_degree_abbrev(degree):
	subs = {
		'Bachelor of Science': 'BSc',
		'Master of Science': 'MSc',
		'Master of Science, Applied': 'MScA',
		'Bachelor of Arts': 'BA',
		'Master of Arts': 'MA',
		'Bachelor of Arts and Science': 'BAsc',
		'Bachelor of Engineering': 'BEng',
		'Bachelor of Software Engineering': 'BSE',
		'Master of Engineering': 'MEng',
		'Bachelor of Commerce': 'BCom',
		'Licentiate in Music': 'LMus',
		'Bachelor of Music': 'BMus',
		'Master of Music': 'MMus',
		'Bachelor of Education': 'BEd',
		'Master of Education': 'MEd',
		'Bachelor of Theology': 'BTh',
		'Master of Sacred Theology': 'STM',
		'Master of Architecture': 'MArch',
		'Bachelor of Civil Law': 'BCL',
		'Bachelor of Laws': 'LLB',
		'Master of Laws': 'LLM',
		'Bachelor of Social Work': 'BSW',
		'Master of Social Work': 'MSW',
		'Master of Urban Planning': 'MUP',
		'Master of Business Administration': 'MBA',
		'Master of Management': 'MM',
		'Bachelor of Nursing (Integrated)': 'BNI',
		'Doctor of Philosophy': 'PhD',
		'Doctor of Music': 'DMus'
	} #Most of these degrees probably won't work with minervac, but this list may be slightly useful
	for sub in subs:
		degree = degree.replace(sub,subs[sub])
	
	return degree

def get_program_abbrev(program):
	program = program.replace('Concentration ','') #Who cares?
	majors = []
	minors = []
	other = []

	for line in program.split("\n"):
		if line.startswith("Major"):
			majors.append(line.split("Major ")[1])
		elif line.startswith("Minor"):
			minors.append(line.split("Minor ")[1])
		else:
			other.append(line)

	
	program = ", ".join(majors)
	if minors:
		program += "; Minor " + ", ".join(minors)
	if other:
		program += " [" + ", ".join(other) + "]"

	return program

def get_grade_explanation(grade,normal_grades = False):
	explanation = { 
		'HH': 'To be continued',
		'IP': 'In progress',
		'J': 'Absent',
		'K': 'Incomplete',
		'KE': 'Further extension granted',
		'K*': 'Further extension granted',
		'KF': 'Incomplete - Failed',
		'KK': 'Completion requirement waived',
		'L': 'Deferred',
		'LE': 'Deferred - extension granted',
		'L*': 'Deferred - extension granted',
		'NA': 'Grade not yet available',
		'&&': 'Grade not yet available',
		'NE': 'No evaluation',
		'NR': 'No grade reported by the instructor (recorded by the Registrar)',
		'P': 'Pass',
		'Q': 'Course continues in following term',
		'R': 'Course credit',
		'W': 'Permitted to withdraw',
		'WF': 'Withdraw - failing',
		'WL': 'Faculty permission to withdraw from a deferred examination',
		'W--': 'No grade: student withdrew from the University',
		'--': 'No grade: student withdrew from the University',
		'CO': 'Complete [Academic Integrity Tutorial]',
		'IC': 'Incomplete [Academic Integrity Tutorial]'
	}

	normal_explanation = {
		'A': '85 - 100',
		'A-': '80 - 84',
		'B+': '75 - 79',
		'B': '70 - 74',
		'B-': '65 - 69',
		'C+': '60 - 64',
		'C': '55 - 59',
		'D': '50 - 54',
		'F': '0 - 49',
		'S': 'Satisfactory',
		'U': 'Unsatisfactory'
	}

	if normal_grades:
		explanation.extend(normal_explanation)

	if grade in explanation:
		return explanation[grade]
	else:
		return ''

def lg_to_gpa(letter_grade):
	return {'A': '4.0','A-': '3.7','B+': '3.3', 'B': '3.0', 'B-': '2.7', 'C+': '2.3', 'C': '2.0','D': '1.0','F': '0'}[letter_grade]
	
