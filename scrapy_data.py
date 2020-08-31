# -*- coding: utf-8 -*-

import datetime
import argparse
import csv, json
import os, re

try:
    import requests
except ModuleNotFoundError as e:
    os.system('pip install requests')

try:
    from rich.progress import track
except ModuleNotFoundError as e:
    os.system('pip install rich')

def dateRange(start, end, format="%Y-%m-%d-%H-%M"):
    '''
    generate the date from start time to end time
    start: start time, format: '2020-01-01-00-00'
    end: endtime, the format same to start time, endtime must greater then start time
    format: respond to start and end time format
    '''
    start_time = datetime.datetime.strptime(start, format)
    end_time = datetime.datetime.strptime(end, format)
    time_delta = end_time - start_time
    # total minutes
    minutes = (time_delta.seconds + time_delta.days*24*3600) // 60
    cur_time = start_time - datetime.timedelta(minutes=1)
    for minute in range(minutes+1):
        cur_time = cur_time + datetime.timedelta(minutes=1)
        yield datetime.datetime.strftime(cur_time, "%Y-%m-%d-%H-%M")

def dateLength(start, end, format="%Y-%m-%d-%H-%M"):
    '''
    compute the total length of datelist
    purpose: estimate the scrapy time
    '''
    start_time = datetime.datetime.strptime(start, format)
    end_time = datetime.datetime.strptime(end, format)
    time_delta = end_time - start_time
    # total minutes
    minutes = (time_delta.seconds + time_delta.days * 24 * 3600) // 60
    return minutes

def area_code_find(area_list, area_name):
    '''
    find the area code by area name
    '''
    for area in area_list.values():
        if area_name == area['obtname']:
            code = area['obtid']
    return code

def scrapy_area_list(headers, data):
    '''
    scrapy the area-code dict
    each area corresponds to a number code
    '''
    url = 'https://weather.121.com.cn/szqx/api/obt/list.do'
    area_data = dict()
    area_data['tokenId'] = data['tokenId']
    area_data['token'] = data['token']

    json_data = requests.post(url, headers=headers, data=data).json()
    # print(json_data)

    return json_data['data']

def update_token(headers, data):
    '''
    the token and token_id in request form data will changed every serval hours
    so we need to update the token from time to time
    '''
    # update the token
    token_url = 'https://weather.121.com.cn/szqx/api/token.js'
    token_data = requests.get(token_url, headers).text
    ex = 'win.szqbl.token="(.*?)";win.szqbl.tokenId="(.*?)";}'
    tokenlist = re.findall(ex, token_data, re.S)
    data['tokenId'] = tokenlist[0][1]
    data['token'] = tokenlist[0][0]

    return data


def scrapy_data(area = ['水围','珠光'], qtype='RainM30', start_time='2019-09-02-00-09', end_time='2019-09-30-00-20'):
    # create a csv file to store data
    file_name = 'data_' + '_'.join(area) + '.csv'
    if not os.path.exists(file_name):
        head = ['time', *area]
        with open(file_name, 'w', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(head)
    # url
    url = 'https://weather.121.com.cn/szqx/api/obt/data.do'
    # user the header
    headers = {
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36'
    }
    data = {
        'dataType': 'json',
        'area': 'all',
        'datetime': 'Dynamic generation',
        'qType': qtype,
        'tokenId': 'Dynamic acquisition',
        'token': 'Dynamic acquisition'
    }
    # Encapsulation of parameters
    min_list = dateRange(start_time, end_time)
    total_mimutes = dateLength(start_time, end_time)

    # Place name converted to code name
    try:
        # try to scrap the area code
        # if the lisence is outline, need to access the token again
        area_list = scrapy_area_list(headers, data)
    except:
        # access the token again
        data = update_token(headers, data)
        area_list = scrapy_area_list(headers, data)

    name_code = {}
    for area_index in area:
        area_code = area_code_find(area_list, area_index)
        name_code[area_index] = area_code

    print('%-20s' % ('time'), end=' ')
    for area_index in area:
        print('%10s' % (area_index), end=' ')
    print('\n')
    rows = []
    for index, time_min in track(enumerate(min_list), total=total_mimutes, description='爬取中...'):

        # every 12 hours, update the token, not update in the start time
        if (index//60) % 12 == 0 and time_min != 0:
            data = update_token(headers, data)

        # fill the time in the dict data
        data['datetime'] = time_min
        json_data = requests.post(url, headers=headers, data=data).json()
        if not json_data['data']:
            raise ValueError('返回数据为空，数据库中无 %s 的数据, 请检查start_time!' % (time_min))
        print('%-20s' % (time_min), end='\t')
        row = [time_min]
        for area_index in area:
            print('%10s' % (json_data['data'][name_code[area_index]]), end=' ')
            row.append(json_data['data'][name_code[area_index]])
        print('\n')
        rows.append(row)
        # every 6 hours data, write the rows into file
        if (index % 360 == 0) and (index != 0) :
            with open(file_name, 'a+') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            print('*'*20, '节点保存', '*'*20)


if __name__ == '__main__':

    # parser =argparse.ArgumentParser(description='input the area and time')
    # # set area
    # parser.add_argument('--area', '-a',
    #                     default=['水围', '珠光', '金龟'],
    #                     help='area choose, use list format like ["水围", "珠光"]')
    #
    # # set start time
    # parser.add_argument('--start','-s',
    #                     default='2019-09-02-00-00',
    #                     help='start time, format: %YYYY-%MM-%DD-%HH-%mm')
    #
    # # set end time
    # parser.add_argument('--end', '-e',
    #                    default='2019-09-03-00-00',
    #                    help='end time, format: %YYYY-%MM-%DD-%HH-%mm')
    #
    # args = parser.parse_args()
    config = json.load(open('config.json', encoding="utf-8"))
    scrapy_data(area=config['area'],
                qtype=config['qType'],
                start_time=config['start_time'],
                end_time=config['end_time'])

