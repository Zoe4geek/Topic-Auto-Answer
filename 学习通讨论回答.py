import requests
from lxml import etree
import re
import pandas
import datetime
import uuid
import base64
import time


def get_courses_list(fsession):

    courses_header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/98.0.4758.102 Safari/537.36 Edg/98.0.1108.62 '
    }
    courses_url = 'http://mooc2-ans.chaoxing.com/visit/courses/list'
    courses_res = fsession.get(url=courses_url, headers=courses_header)
    courses_res_html = courses_res.text

    # 获取所有课程信息，存在 courses_list 中
    courses_tree = etree.HTML(courses_res_html)
    courses_div_list = courses_tree.xpath('//*[@id="courseList"]/li')

    temp_courses_list = []

    for course_div in courses_div_list:
        course_not_open = course_div.xpath('.//*[@class="not-open-tip"]')
        if course_not_open:
            not_open_tip = 1
        else:
            not_open_tip = 0
        course_info = course_div.xpath('.//div[@class="course-info"]//a/@href')
        course_url = course_info[0]

        course_title = str(course_div.xpath('.//*[@class="course-name overHidden2"]/@title')[0])
        course_id = str(course_div.xpath('.//*[@class="courseId"]/@value')[0])
        class_id = str(course_div.xpath('.//*[@class="clazzId"]/@value')[0])

        cpi_ex = '.*?cpi=(.*?)&'
        if re.findall(cpi_ex, course_url):
            cpi = re.findall(cpi_ex, course_url)[0]

            course_dic = {
                'title': course_title,
                'courseId': course_id,
                'classId': class_id,
                'cpi': cpi,
                'not_open_tip': not_open_tip
            }
        else:
            course_dic = {
                'title': course_title,
                'courseId': course_id,
                'classId': class_id,
                'not_open_tip': not_open_tip
            }

        temp_courses_list.append(course_dic)

    return temp_courses_list, fsession


if __name__ == "__main__":
    users_info_lists = []
    user_info_csv = pandas.read_csv('topic_user.csv', encoding='utf-8', converters={'user': str})

    for i in range(len(user_info_csv)):
        password_str = user_info_csv['password'][i]
        password_ex = "(.*?)\n"
        password_base64_raw = base64.encodebytes(password_str.encode('utf8')).decode()
        password_base64 = re.findall(password_ex, password_base64_raw)[0]
        user_info = {'user': user_info_csv['user'][i], 'password': password_base64,
                     'email': user_info_csv['email'][i], 'name': user_info_csv['name'][i]}
        users_info_lists.append(user_info)

    for user_info in users_info_lists:
        time.sleep(10)

        session = requests.Session()

        # 登录学习通，拿到cookie
        chaoxing_login_header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/98.0.4758.102 Safari/537.36 Edg/98.0.1108.62 '
        }
        chaoxing_login_url = 'http://passport2.chaoxing.com/fanyalogin'
        chaoxing_login_data = {
            'fid': '-1',
            'uname': user_info['user'],
            'password': user_info['password'],
            'refer': 'http://i.chaoxing.com',
            't': 'true',
            'forbidotherlogin': '0',
            'validate': ''
        }

        session.post(url=chaoxing_login_url, data=chaoxing_login_data, headers=chaoxing_login_header)

        (courses_list, session) = get_courses_list(session)

        for course in courses_list:
            if course['not_open_tip'] == 0:
                course_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/98.0.4758.102 Safari/537.36 Edg/98.0.1108.62 '
                }
                course_param = {
                    'courseid': course['courseId'],
                    'clazzid': course['classId'],
                    'cpi': course['cpi'],
                    'ismooc2': '1'
                }
                course_url = 'http://mooc1.chaoxing.com/visit/stucoursemiddle'
                course_res = session.get(url=course_url, params=course_param, headers=course_headers)

                topics_list_len = 20
                page_num = 1
                last_reply_time = 0

                topics_list = []
                while topics_list_len == 20:
                    topics_list_headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                      'Chrome/98.0.4758.102 Safari/537.36 Edg/98.0.1108.62 '
                    }

                    tags = 'classId0000001,classId' + course['classId'] + ',courseId' + course['courseId']
                    topics_list_param = {
                        'folder_uuid': '',
                        'page': str(page_num),
                        'pageSize': '20',
                        'kw': '',
                        'last_reply_time': str(last_reply_time),
                        'tags': tags,
                        '_': '1647473256129'
                    }

                    course_tree = etree.HTML(course_res.text)
                    course_bbs_id = course_tree.xpath('//*[@id="bbsid"]/@value')[0]
                    topics_list_url = 'http://groupweb.chaoxing.com/course/topic/' + course_bbs_id + '/getTopicList'

                    topics_list_res = session.get(url=topics_list_url, params=topics_list_param,
                                                  headers=topics_list_headers)
                    topics_list_dic = topics_list_res.json()

                    is_empty_ex = '.*?datas.*?'
                    if re.match(is_empty_ex, topics_list_res.text) is None:
                        topics_list_len = 0
                    else:
                        datas_list = topics_list_dic['datas']

                        for data_dic in datas_list:
                            ftime = data_dic['ftime']
                            today = datetime.datetime.today()
                            if re.match('昨天', ftime):
                                yesterday = today + datetime.timedelta(days=-1)
                                data_year = str(yesterday.year)
                                data_month = str(yesterday.month)
                                data_day = str(yesterday.day)
                            elif re.match(r'\d{4}.*?', ftime):
                                data_year = re.findall(r'(\d{4}).*?', ftime)[0]
                                data_month = re.findall(r'\d{4}-(\d{2}).*?', ftime)[0]
                                data_day = re.findall(r'\d{4}-\d{2}-(\d{2}).*?', ftime)[0]
                            elif re.match(r'\d{2}-.*?', ftime):
                                data_year = str(today.year)
                                data_month = re.findall(r'(\d{2}).*?', ftime)[0]
                                data_day = re.findall(r'\d{2}-(\d{2}).*?', ftime)[0]
                            else:
                                data_year = str(2022)
                                data_month = str(1)
                                data_day = str(1)

                            data_uuid = data_dic['uuid']
                            data_bbsid = data_dic['bbsid']
                            topic_dic = {'uuid': str(data_uuid), 'bbsid': str(data_bbsid), 'lastValue': '',
                                         'year': data_year, 'month': data_month, 'day': data_day}
                            topics_list.append(topic_dic)

                        topics_list_len = len(topics_list_dic['datas'])
                        page_num = page_num + 1
                        last_reply_time = topics_list_dic['poff']['lastValue']

                for topic in topics_list:
                    if int(topic['year']) == 2022 and int(topic['month']) >= 3 or int(topic['year']) >= 2023:
                        answers_list = []
                        answers_len = 20
                        answers_page = 0
                        answers_num = 0
                        answer_longest = ''
                        longest_len = 0
                        have_answered = 0
                        while answers_len == 20 and answers_page < 5:

                            answers_page = answers_page + 1
                            topic_header = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
                                              'like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.36 '
                            }
                            topic_param = {
                                'bbsid': topic['bbsid'],
                                'uuid': topic['uuid'],
                                'tag': '',
                                'order': '2',
                                'lastValue': topic['lastValue']
                            }
                            topic_url = 'http://groupweb.chaoxing.com/pc/invitation/getReplyList'
                            topic_res = session.get(url=topic_url, params=topic_param, headers=topic_header)
                            topic_json = topic_res.json()

                            datas_list = topic_json['datas']
                            for datas in datas_list:
                                answer_username = datas['creater_name']
                                if answer_username == user_info['name']:
                                    have_answered = 1
                                answer_content = datas['content']
                                answer_uuid = datas['uuid']
                                answer_dic = {'creater_name': answer_username,
                                              'uuid': answer_uuid}
                                answers_list.append(answer_dic)
                                answers_num = answers_num + 1

                                if len(answer_content) > longest_len:
                                    answer_longest = answer_content
                                    longest_len = len(answer_content)

                            answers_len = len(topic_json['datas'])
                            if len(topic_json['datas']) == 20:
                                topic['lastValue'] = topic_json['poff']['lastValue']

                        if have_answered == 0 and answers_num >= 5:
                            answer_topic_headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
                                              'like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.36 '
                            }
                            answer_topic_data = {
                                'courseId': course['courseId'],
                                'classId': course['classId'],
                                'replyId': '-1',
                                'uuid': str(uuid.uuid4()),
                                'topic_content': answer_longest,
                                'anonymous': ''
                            }
                            answer_topic_url = 'https://groupweb.chaoxing.com/pc/invitation/' + topic['uuid'] + '/addReplys'
                            session.post(url=answer_topic_url, data=answer_topic_data, headers=answer_topic_headers)
                            print(course['title'] + ' ' + topic['uuid'])
