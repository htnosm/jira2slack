# jira2slack
Notify JIRA activity to Slack

## Description

JIRA の Activity Streams を Slack へ通知する  
Slack Integration や RSS が用意されているが、何かしらの理由で利用できない場合の代替策。

* [Activity Streams](https://developer.atlassian.com/server/framework/atlassian-sdk/activity-streams/)
    * https://jira.atlassian.com/activity
* [Jira と Slack を連携させる \| Slack](https://slack.com/intl/ja-jp/help/articles/218475657-Jira-%E3%81%A8-Slack-%E3%82%92%E9%80%A3%E6%90%BA%E3%81%95%E3%81%9B%E3%82%8B)

## Requirements

* python 3.8+
* docker

## Installation

```
# ダウンロード
git clone https://github.com/htnosm/jira2slack.git
cd jira2slack

# 設定ファイル作成
## 未指定項目は default.yml の値が使用される
cat <<_EOF > jira2slack/etc/TESTPJ.yml
jira_key: 'Your JIRA Project Key'
jira_url: 'https://jira.example.com'
auth_user: 'Your Username'
auth_password: 'Your Password'
slack_webhook_url: 'Your Slack Incoming Webhook URL'
slack_channel: 'Your Slack Channel # e.g.) "#general'
slack_username: 'Slack bot username'
_EOF
```

## Usage

```
# 起動 (バックグラウンド -d 可)
docker-compose up
# 停止
docker-compose down
```

### Dockerを使用しないで起動する

```
pip install -r jira2slack/requirements.txt

CHECK_URL=https://example.com ./jira2slack/src/docker-entrypoint.sh
```

### 初回実行時等で、通知から現在日時より前を除外する

```
cat <<_EOF > ./jira2slack/var/last_publish.TESTPJ.json
{
  "ts": $(date +'%s')
}
_EOF
```

## Known Issue

### アクティビティ取得失敗

```
<msg name="gadget.activity.stream.error.loading.feed">最近のアクティビティを取得しようとしたときにエラーが発生しました。</msg>
```

* [Invalid Character Causing Activity Stream Not Rendering Properly \(Invalid white space character in text to output\) \- Atlassian Documentation](https://confluence.atlassian.com/jirakb/invalid-character-causing-activity-stream-not-rendering-properly-invalid-white-space-character-in-text-to-output-432276561.html)
    * 特殊文字( "<",">" ?) を含んだ場合に rss 不正で取得不可となる
    * IncompleteRead を Catch、取得行数減らして再試行する処理を追加済
