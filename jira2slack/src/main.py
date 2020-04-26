#! /usr/bin/env python3
# -*- coding: utf8 -*-

import os
import io
import requests
import feedparser
from datetime import datetime,timedelta
import argparse
import bs4
from bs4 import BeautifulSoup
import slackweb
import time
import json
import yaml


def arg_parse():
  parser = argparse.ArgumentParser(description='')
  parser.add_argument('configYAML', type=str, help='e.g.) etc/config.yml')
  return(parser.parse_args())


def config_parse(config_file):
  default_config = './etc/default.yml'
  options = {}
  if os.path.exists(default_config):
    with open(default_config) as file:
      options = yaml.safe_load(file.read())

  if os.path.exists(config_file):
    with open(config_file) as file:
      params = yaml.safe_load(file.read())
      options.update(params)
  else:
    print('"{file}" No such file'.format(file = config_file))
    raise Exception

  return options


def get_jira_activity(jira_key, jira_url, jira_max_results, auth_user, auth_password, **kwargs):
  jira_url = (jira_url + '/activity?maxResults=' + str(jira_max_results)
   + '&streams=key+IS+' + jira_key
   + '&providers=thirdparty+dvcs-streams-provider+issues&os_authType=basic&title=undefined')

  try:
    resp = requests.get(jira_url, timeout=15.0, auth=(auth_user, auth_password))
    print(resp)
  except requests.ReadTimeout:
    print ("Timeout when reading RSS %s", jira_url)
    return
  except requests.exceptions.ChunkedEncodingError as e:
    # [Invalid Character Causing Activity Stream Not Rendering Properly \(Invalid white space character in text to output\) \- Atlassian Documentation](https://confluence.atlassian.com/jirakb/invalid-character-causing-activity-stream-not-rendering-properly-invalid-white-space-character-in-text-to-output-432276561.html)
    print ('ChunkedEncodingError: ' + str(e))
    if "IncompleteRead" in str(e):
      jira_max_results = str(int(int(jira_max_results) / 2))
      if int(jira_max_results) > 10:
        print("Set jira_max_results = " + jira_max_results)
        main()
    return
  except Exception as e:
    print ('Error: ' + str(e))
    return

  feed = io.BytesIO(resp.content)
  r = feedparser.parse(feed)
  return(r)


def parse_issue_title(issue_key, soup_title):
  content_text = None
  for i in range(len(soup_title.contents)):
    if type(soup_title.contents[i]) is bs4.element.Tag:
      content_text = soup_title.contents[i].text
    else:
      content_text = soup_title.contents[i].strip()
    if issue_key in content_text:
      return(content_text.replace(issue_key, ''))


def parse_issue_action(issue_key, issue_title, soup_title):
  action = ''
  for i in range(len(soup_title.contents)):
    if i > 0:
      if type(soup_title.contents[i]) is bs4.element.Tag:
        action = action + soup_title.contents[i].text
      else:
        action = action + soup_title.contents[i].strip()
    if issue_key in action:
      action = action.replace(issue_key + issue_title, '')
  return(action)


def parse_entries(r, last_publish_ts):
  count = 0
  contents = []
  for entry in r.entries:
    content = {}
    #print ('--------------------')
    #print (count)
    count = count + 1
    # author
    content['author'] = entry['author']
    # published
    published_utc = datetime.strptime(entry['published'], '%Y-%m-%dT%H:%M:%S.%fZ')
    content['published_epoc'] = int(published_utc.timestamp())
    published_jst = published_utc + timedelta(hours=9)
    content['published'] = published_jst.strftime('%Y-%m-%d %H:%M:%S')

    if content['published_epoc'] <= last_publish_ts:
      continue

    # issues
    content['issue_url'] = entry['link']
    link_paths = content['issue_url'].split('/')
    content['issue_key'] = link_paths[len(link_paths) - 1]
    # title
    soup_title = BeautifulSoup(entry['title'], "html.parser")
    content['issue_title'] = parse_issue_title(content['issue_key'], soup_title)
    if content['issue_title'] is None:
      content['issue_title'] = ''
    #print(content['issue_key'] + content['issue_title'])
    # action
    content['action'] = parse_issue_action(content['issue_key'], content['issue_title'], soup_title)
    #print(content['action'])
    # comment
    comment = None
    if content['action'] in ['comment', 'コメント'] or content['issue_title'] == '':
      soup_summary = BeautifulSoup(entry['summary'], "html.parser")
      comment = soup_summary.text
      if comment is not None:
        comment = "```" + comment + "\n```"
    content['comment'] = comment
    #print (content)
    contents.append(content)

  return (contents)


def post_contents(last_publish_file, contents, slack_color, **kwargs):
  message_text, bef_author, bef_title = '', '', ''
  for i in range(len(contents)):
    attachment = {}
    title = contents[i]['issue_key'] + contents[i]['issue_title']
    message_text = message_text + contents[i]['published'] + ' | ' + contents[i]['action'] + "\n"
    if contents[i]['comment'] is not None:
      message_text = message_text + "\n" + contents[i]['comment'] + "\n"

    if i < len(contents) - 1 and ( \
      contents[i]['author'] == contents[i + 1]['author'] and \
      contents[i]['issue_key'] == contents[i + 1]['issue_key'] and \
      contents[i]['issue_title'] == contents[i + 1]['issue_title'] \
    ):
      None
    else:
      attachment = {
        "fallback": contents[i]['issue_key'],
        "color": slack_color,
        "title": title,
        "title_link": contents[i]['issue_url'],
        "author_name": contents[i]['author'],
        "text": message_text,
        "ts": contents[i]['published_epoc'],
      }
      slack_notify(last_publish_file, attachment, **kwargs)
      message_text, bef_author, bef_title = '', '', ''


def slack_notify(last_publish_file, attachment, slack_webhook_url, slack_channel, slack_username, slack_icon_emoji, **kwargs):
  slack = slackweb.Slack(url=slack_webhook_url)
  attachments = []
  # ts が UTC 出力のため Slack へは連携しない
  del_ts_attachment = attachment.copy()
  del del_ts_attachment['ts']
  attachments.append(del_ts_attachment)
  print(attachments)
  try:
    r = slack.notify(channel=slack_channel, username=slack_username, icon_emoji=slack_icon_emoji, attachments=attachments)
    with open(last_publish_file, 'w') as f:
      json.dump(attachment,f,indent=4)
  except Exception as e:
    print ('Error: ' + str(e))
    return
  time.sleep(1)


def main(args=None):
  args = arg_parse()
  try:
    options = config_parse(args.configYAML)
  except Exception:
    return
  #print(options)

  print(str(datetime.now()) + ' ' + options['jira_key'] + ' start')

  last_publish_file = './var/last_publish.' + options['jira_key'] + '.json'
  last_publish_ts = 0
  if os.path.exists(last_publish_file):
    try:
      with open(last_publish_file, 'r') as f:
        last_publish = json.load(open(last_publish_file))
        last_publish_ts = last_publish['ts']
    except Exception as e:
      print ('Error: ' + str(e))
      return

  print('last_publish_ts: ' + str(last_publish_ts))

  r = get_jira_activity(**options)
  if r is not None:
    print('activity entries: ' + str(len(r.entries)))
    contents = parse_entries(r, last_publish_ts)
    contents_sorted = sorted(contents, key=lambda x:x['published_epoc'])
    print('publish entries:' + str(len(contents_sorted)))
    r = post_contents(last_publish_file, contents_sorted, **options)

  print(str(datetime.now()) + ' ' + options['jira_key'] + ' end')


if __name__ == '__main__':
  main()
