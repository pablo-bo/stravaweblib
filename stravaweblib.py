# -*- coding: utf-8 -*-
import json
import requests
import lxml.html

# TODO
# randomize UA
##  "User-Agent" : random.choice(LoadUserAgents())}

DEBUG = False

def debug_print(message):
    if DEBUG: 
        print(message)
        
def extract(parser, xpath):
    result = None
    res_lst = parser.xpath(xpath)
    if res_lst:
        result = res_lst[0]
    return result

        
BASE_STRAVA_SITE_URL = 'https://www.strava.com'

version__ = '0.0.1'

class StravaWebClient(object):
##    strava_session = None
##    csrf_token     = None

    def  __init__(self):
        self.strava_session = None
        csrf_token          = None

    def login(self, login, password): 
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.0; rv:14.0) Gecko/20100101 Firefox/14.0.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-en,en;q=0.8,en-us;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'DNT': '1'
        }
        session = requests.session()
        session.headers = headers

        page = lxml.html.fromstring(session.get(BASE_STRAVA_SITE_URL+'/login/').content)
        form = page.forms[0]
        form.fields['email'] = login
        form.fields['password'] = password

        r = session.post( BASE_STRAVA_SITE_URL + form.action, data=form.form_values())
        ## CSRF 1 ##
        local_csrf_token = form.fields['authenticity_token']
        #debug_print('local csrf : '+local_csrf_token)

        self.strava_session = session
        self.csrf_token     = local_csrf_token

        # check login
        parser = lxml.html.fromstring(r.text)
        # if found li class="logged_out_nav" - not logged (this is registration button)
        reg_button = parser.xpath(".//li[@class='logged_out_nav']")
        signin=False
        if ( len(reg_button)==0 ):
            signin=True
            
        return signin # implemented chek on login is true
    
    def logout(self):
        #self.strava_session.config['keep_alive'] = False
        self.strava_session.post(BASE_STRAVA_SITE_URL, headers={'Connection':'close'})
        
    def check_login(self):
        r = self.strava_session.get( BASE_STRAVA_SITE_URL + '/dashboard/')
        parser = lxml.html.fromstring(r.text)
        # if found li class="logged_out_nav" - not logged (this is registration button)
        reg_button = parser.xpath(".//li[@class='logged_out_nav']")
        signin=False
        if ( len(reg_button)==0 ):
            signin=True
            
        return signin

    def get_my_name(self):
        name=''
        r = self.strava_session.get( BASE_STRAVA_SITE_URL + '/athlete/calendar')
        parser = lxml.html.fromstring(r.text)
        lst_athlethe_name = parser.xpath("//title")
        
        if len(lst_athlethe_name)>0:
            name = lst_athlethe_name[0].text_content()
        
        first_name = name.split('|')
        return first_name[1].strip()
    
    def get_name_athlethe(self, athlethe_id):
        name=''
        r = self.strava_session.get(BASE_STRAVA_SITE_URL+'/athletes/'+athlethe_id)
        parser = lxml.html.fromstring(r.text)
        # name athlet
        lst_athlethe_name = parser.xpath('//title')
        if len(lst_athlethe_name)>0:
            name = lst_athlethe_name[0].text_content()
        first_name = name.split('|')
            
        #debug_print(athlethe_name)
        return first_name[0].strip()

    def get_followers(self, athlethe_id):
        # followers
        result=[]
        urls = []
        start_url = BASE_STRAVA_SITE_URL+'/athletes/'+athlethe_id+'/follows?type=followers'
        r = self.strava_session.get(start_url)
        parser = lxml.html.fromstring(r.text)
        #pagination
        followers_pages = parser.xpath(".//ul[@class='pagination']/./li")
        first_page = 1
        last_page  = 1
        # followers_pages - not empty
        if len(followers_pages)>0:
            last_page  = int(followers_pages[-2][0].text)
        # generate page urls    
        for p in range(first_page, last_page+1):
            urls.append(BASE_STRAVA_SITE_URL+'/athletes/'+athlethe_id+'/follows?page='+str(p)+'&type=followers')
        #extract 
        for url in urls:
            r = self.strava_session.get(url)
            parser = lxml.html.fromstring(r.text)
            following_li = parser.xpath(".//ul[substring(@class, 1, 9)='following']/./li") # bugfix for auth athlethe followers
            for f in following_li:
                result.append(f.get("data-athlete-id"))
                
        return result

    def get_last_activities(self, athlethe_id):
        result_lst_act_id = []
        r2 = self.strava_session.get(BASE_STRAVA_SITE_URL+'/athletes/'+athlethe_id)
        parser = lxml.html.fromstring(r2.text)
        ## xpath string for single activity
        ##.//div[substring(@id, 1, 8)='Activity']
        lst_single_activity = parser.xpath(".//div[substring(@id, 1, 8)='Activity']")
        debug_print('single '+str(lst_single_activity))
        ## xpath string for group activity
        ##.//li[substring(@id, 1, 8)='Activity'] // all athlethes in group activity
        lst_group_activity = parser.xpath(".//li[substring(@id, 1, 8)='Activity']")
        debug_print('group '+str(lst_group_activity))
        ## xpath string for group activity for selected athlete
        ##.//li[substring(@id, 1, 8)='Activity']/*[@href="/athletes/athlethe_id"]/..
        lst_athlethe_act_in_group_activity = parser.xpath(".//li[substring(@id, 1, 8)='Activity']/*[@href='/athletes/"+athlethe_id+"']/..")
        debug_print('ath in group '+str(lst_athlethe_act_in_group_activity ))

        for l in lst_single_activity:
            id_act = l.attrib['id']
            act = id_act.split('-')[1]
            result_lst_act_id.append(act)
            
        for l in lst_athlethe_act_in_group_activity:
            id_act = l.attrib['id']
            act = id_act.split('-')[1]
            result_lst_act_id.append(act)        

        return result_lst_act_id
        ## END FIND ACTIVITIES ###

    def get_activities_by_interval(self, athlethe_id, interval_year, interval_num, interval_type):

        headers_int = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.0; rv:14.0) Gecko/20100101 Firefox/14.0.1',
            'Accept': 'text/javascript, application/javascript, application/ecmascript, application/x-ecmascript',
            'Accept-Language': 'ru-ru,ru;q=0.8,en-us;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'DNT': '1',
            'X-CSRF-Token': self.csrf_token,
            'Referer': 'https://www.strava.com/athletes/'+str(athlethe_id),
            'X-Requested-With':'XMLHttpRequest'
        }
        self.strava_session.headers = headers_int
        
        result_lst_act_id = []
        act_int_url = BASE_STRAVA_SITE_URL+'/athletes/'+athlethe_id+\
                      '#interval?interval='+str(interval_year)+str(interval_num)+\
                      '&interval_type='+interval_type+'&chart_type=miles&year_offset=0'
        debug_print(act_int_url)
        payload = {'interval': str(interval_year)+str(interval_num),
                   'interval_type': interval_type,
                   'chart_type': 'miles', 'year_offset': 0}
        r2 = self.strava_session.get(act_int_url, params=payload)
        parser = lxml.html.fromstring(r2.text)
        
        ## xpath string for single activity
        ##.//div[substring(@id, 1, 8)='Activity']
        lst_single_activity = parser.xpath(".//div[substring(@id, 1, 8)='Activity']")
        debug_print('single '+str(lst_single_activity))
        ## xpath string for group activity
        ##.//li[substring(@id, 1, 8)='Activity'] // all athlethes in group activity
        lst_group_activity = parser.xpath(".//li[substring(@id, 1, 8)='Activity']")
        debug_print('group '+str(lst_group_activity))
        ## xpath string for group activity for selected athlete
        ##.//li[substring(@id, 1, 8)='Activity']/*[@href="/athletes/athlethe_id"]/..
        lst_athlethe_act_in_group_activity = parser.xpath(".//li[substring(@id, 1, 8)='Activity']/*[@href='/athletes/"+athlethe_id+"']/..")
        debug_print('ath in group '+str(lst_athlethe_act_in_group_activity ))

        for l in lst_single_activity:
            id_act = l.attrib['id']
            act = id_act.split('-')[1]
            result_lst_act_id.append(act)
            
        for l in lst_athlethe_act_in_group_activity:
            id_act = l.attrib['id']
            act = id_act.split('-')[1]
            result_lst_act_id.append(act)        

        return result_lst_act_id
        ## END FIND ACTIVITIES ###

    def is_kudosable_activity(self, activity_id):
        kudos_url = BASE_STRAVA_SITE_URL +'/feed/activity/'+activity_id+'/kudos'
        headers_kudos = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.0; rv:14.0) Gecko/20100101 Firefox/14.0.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-ru,ru;q=0.8,en-us;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'DNT': '1',
            'X-CSRF-Token': self.csrf_token
        }
        self.strava_session.headers = headers_kudos
        responce = self.strava_session.get(kudos_url) # return JSON
        data = json.loads(responce.text) #загружаем из файла данные в словарь data
        return data['kudosable']

    def get_kudos(self, activity_id):
        '''
        return list of athlethes who kudosed this activity
        result is list of dict
        each record in list - kudo from athlete presentation as dictionari
        {'id': 1, 'url': '/athletes/19098301', 'name': 'username', 'firstname': 'user',
         'avatar_url': 'https://.../medium.jpg', 'member_type': '', 'location': 'Amsterdam',
         'is_private': False, 'is_following': None}

        '''
        
        # example url   #https://www.strava.com/feed/activity/850171066/kudos
        kudo_url = BASE_STRAVA_SITE_URL +'/feed/activity/'+activity_id+'/kudos'
        #debug_print(kudo_url)
        headers_kudo = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.0; rv:14.0) Gecko/20100101 Firefox/14.0.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-ru,ru;q=0.8,en-us;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'DNT': '1',
            'X-CSRF-Token': self.csrf_token
        }
        self.strava_session.headers = headers_kudo
        responce = self.strava_session.get(kudo_url) # return JSON
        fh=responce.text
        data = json.loads(fh) #загружаем из файла данные в словарь data
        #for dt in data['athletes']:
        #        print (dt['name'])
        lst_kudos = data['athletes']
        #debug_print('kudos '+str(lst_kudos))
      
        return lst_kudos
    
    ## GIVE KUDO ##
    def give_kudo(self, activity_id):
        # example url   #https://www.strava.com/feed/activity/847786020/kudo
        kudo_url = BASE_STRAVA_SITE_URL +'/feed/activity/'+activity_id+'/kudo'
        headers_kudo = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.0; rv:14.0) Gecko/20100101 Firefox/14.0.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-ru,ru;q=0.8,en-us;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'DNT': '1',
            'X-CSRF-Token': self.csrf_token
        }
        self.strava_session.headers = headers_kudo
        responce = self.strava_session.post(kudo_url)
        return responce
    
    def get_activity_photo(self, activity_id):
        '''
        return list of dict contained keys 'large', 'thumbnails' urls of foto
        '''
        # xpath = .//script[substring(text(),4,29)='function renderInstagram(map)']
        activity_url = BASE_STRAVA_SITE_URL +'/activities/'+activity_id
        r = self.strava_session.get(activity_url)
        parser = lxml.html.fromstring(r.text)
        xpath = ".//script[substring(text(),4,29)='function renderInstagram(map)']"
        # TODO need check for right
        script = extract(parser, xpath)
        text_script = script.text
        start = text_script.find('var photosJson = [')# len this string = 18
        end = text_script.find(']')
        return json.loads(text_script[start+17:end+1])
    
    def get_activity_data(self, activity_id):
        activity_url = BASE_STRAVA_SITE_URL +'/activities/'+activity_id
        r = self.strava_session.get(activity_url)
        parser = lxml.html.fromstring(r.text)
        # title
        act_title_lst = parser.xpath('//title')
        if len(act_title_lst)>0:
            act_title = act_title_lst[0].text_content()
            act_title_splited = act_title.split('|')
            act_name = act_title_splited[0].strip()
            act_type = act_title_splited[1].strip()
        # description  
        xpath = ".//div[@class='activity-description']//div[@class='content']/p/text()"
        act_description = extract(parser, xpath)
        # distance
        xpath = ".//*[@id='heading']/div/div/div[2]/ul/li[1]/strong/text()"
        act_dist = extract(parser, xpath)
        xpath = ".//*[@id='heading']/div/div/div[2]/ul/li[1]/strong/abbr/text()"
        act_dist_unit = extract(parser, xpath)
        # elevation
        xpath = ".//*[@id='heading']/div/div/div[2]/ul/li[3]/strong/text()"
        act_elevation = extract(parser, xpath)
        xpath = ".//*[@id='heading']/div/div/div[2]/ul/li[3]/strong/abbr/text()"
        act_elevation_unit = extract(parser, xpath)
        # time
        xpath = ".//*[@id='heading']/div/div/div[2]/ul/li[2]/strong/text()"
        act_moving_time = extract(parser, xpath)
        
        xpath = ".//*[@id='heading']/div/div/div[2]/div[1]/table/tbody[3]/tr/td/text()"
        act_elapsed_time = extract(parser, xpath).strip()
        # speed
        xpath = ".//*[@id='heading']/div/div/div[2]/div[1]/table/tbody[1]/tr/td[1]/text()"
        act_avg_speed = extract(parser, xpath)
        xpath = ".//*[@id='heading']/div/div/div[2]/div[1]/table/tbody[1]/tr/td[1]/abbr/text()"
        act_avg_speed_unit = extract(parser, xpath)
        
        xpath = ".//*[@id='heading']/div/div/div[2]/div[1]/table/tbody[1]/tr/td[2]/text()"
        act_max_speed = extract(parser, xpath)
        xpath = ".//*[@id='heading']/div/div/div[2]/div[1]/table/tbody[1]/tr/td[2]/abbr/text()"
        act_max_speed_unit = extract(parser, xpath)
        
        result = {'name': act_name, 'type':act_type,
                  'description': act_description,
                  'dist':act_dist, 'dist_unit':act_dist_unit,
                  'elevation':act_elevation, 'elevation_unit':act_elevation_unit,
                  'moving_time':act_moving_time,
                  'elapsed_time':act_elapsed_time,
                  'avg_speed':act_avg_speed, 'avg_speed_unit':act_avg_speed_unit,
                  'max_speed':act_max_speed, 'max_speed_unit':act_max_speed_unit }
        return result
        

##-------------- MAIN ------------------##
if __name__ == "__main__":
    print('stravaweblib: v '+version__)
   

