# Jellyfin Music Replay

此文件为 Claude Code (claude.ai/code) 讲解此工具的规范和逻辑。

## 声明

- 文内伪变量引用使用 Python f-string 格式 `{foo}` 表示；Curl 示例 Bash 代码块内用 `${bar}` 表示。
    - 例外：`YEAR_REPLAY_TITLE_TEMPLATE`、`HALF_REPLAY_TITLE_TEMPLATE` 和 `QUARTER_REPLAY_TITLE_TEMPLATE` 内的 `{foo}` 为占位符，是传入的实际内容。
- Curl Bash 脚本仅展示请求内容，实际代码可以使用 Requests 库等方式。
- 本文涉及 Python、SQLite、Jellyfin API 等多种变量格式。实际代码变量名统一使用 Python 惯例的 `snake` 或 `constant` 格式。

## 变量

### 本地存储

保存到本地同名文本文件。有此文件时，优先从本地读取。

| 变量名      | 类型  | 值        | 名称                        |
| ----------- | ----- | --------- | --------------------------- |
| `device_id` | `str` | 随机 UUID | 设备唯一 ID（鉴权请求头用） |

### 内部变量

| 变量名                 | 类型  | 值                        | 说明                       |
| ---------------------- | ----- | ------------------------- | -------------------------- |
| `MEDIA_BROWSER_CLIENT` | `str` | `'Jellyfin Music Replay'` | 客户端名称（鉴权请求头用） |
| `VERSION`              | `str` | `'0.1.0'`                 | 客户端版本（鉴权请求头用） |

### 环境变量

环境变量或存储于 `.env`。有默认值的为可选配置项；`{}` 为占位符，用于程序自动生成。

| 变量名                          | 类型               | 默认值                       | 说明                     |
| ------------------------------- | ------------------ | ---------------------------- | ------------------------ |
| `DEVICE`                        | `str`              | `'Python'`                   | 设备名（鉴权请求头用）   |
| `URL`                           | `str`              |                              | Jellyfin URL             |
| `USERNAME`                      | `str`              |                              | Jellyfin 用户名          |
| `PASSWORD`                      | `str`              |                              | Jellyfin 密码            |
| `PLAYBACK_REPORTING_DB`         | `str`              |                              | 播放报告数据库路径       |
| `IS_PUBLIC`                     | `bool`             | `False`                      | 是否允许公开访问播放列表 |
| `IS_YEAR_REPLAY_DISABLED`       | `bool`             | `False`                      | 是否禁用年回忆生成       |
| `IS_HALF_REPLAY_DISABLED`       | `bool`             | `False`                      | 是否禁用半年回忆生成     |
| `IS_QUARTER_REPLAY_DISABLED`    | `bool`             | `False`                      | 是否禁用季度回忆生成     |
| `YEAR_REPLAY_LIMIT`             | `int`              | `100`                        | 年回忆数量限制           |
| `HALF_REPLAY_LIMIT`             | `int`              | `50`                         | 半年回忆数量限制         |
| `QUARTER_REPLAY_LIMIT`          | `int`              | `25`                         | 季度回忆数量限制         |
| `YEAR_FORMAT`                   | `str` (`strftime`) | `'%Y'`                       | 年份格式化               |
| `YEAR_REPLAY_TITLE_TEMPLATE`    | `str`              | `'Replay {year}'`            | 年回忆标题模板           |
| `HALF_REPLAY_TITLE_TEMPLATE`    | `str`              | `'Replay H{half} {year}'`    | 半年回忆标题模板         |
| `QUARTER_REPLAY_TITLE_TEMPLATE` | `str`              | `'Replay Q{quarter} {year}'` | 季度回忆标题模板         |

## 流程

### 统计数据

统计每首歌的各个周期内播放总时长（**注意**！不是次数），创建排名列表。

1. 从 `{PLAYBACK_REPORTING_DB}` (SQLite) 读取 `PlaybackActivity` 表。
    - 数据表结构示例： @samples/playback_reporting.PlaybackActivity.json 。
2. 筛选 `ItemType` 为 `Audio` 的项目。
3. 以 `ItemName`（**注意**！不是 `ItemId`）为单位，根据 `DateCreated`（单次播放记录创建日期）和 `PlayDuration`（单位：秒），按配置的启用周期和数量限制，分别统计各个周期内播放总时长排行前 `{LIMIT}` 名，降序排列。

### 登录用户

API 密钥连接没有指定用户，无法更新 / 删除项目，故使用用户名和密码登录。

1. 使用 API，携带 `MediaBrowser Client="{MEDIA_BROWSER_CLIENT}", Device="{DEVICE}", DeviceId="{device_id}", Version="{VERSION}"` 鉴权请求头登录。
    - Curl 示例：
        ```bash
        curl -X 'POST' \
          '${URL}/Users/AuthenticateByName' \
          -H 'accept: application/json' \
          -H 'Content-Type: application/json' \
          -H 'Authorization: MediaBrowser Client="${MEDIA_BROWSER_CLIENT}", Device="${DEVICE}", DeviceId="${device_id}", Version="${VERSION}"' \
          -d '{
          "Username": "${USERNAME}",
          "Pw": "${PASSWORD}"
          }'
        ```
    - 响应示例： @samples/response_users_authenticatebyname.json 。
2. 从响应中获取：
    - `AccessToken`
    - 用户 `Id`，用于限定后续操作范围。

此后所有请求，需携带 `MediaBrowser Client="{MEDIA_BROWSER_CLIENT}", Device="{DEVICE}", DeviceId="{device_id}", Version="{VERSION}", Token="{access_token}"` 鉴权请求头。

### 解析项目

处理每个周期排行列表，从数据库的 `ItemName` 映射到 Jellyfin 的项目 `Id`。

1. 从 `ItemName` 匹配信息，结构为 `{专辑艺人} - {名称} ({专辑名称})`
    - **注意**！括号对匹配。最右侧的一对完整 `()` 内为专辑名称；`-` 的两侧分别为专辑艺人和名称。
    - 匹配示例：
        - `ItemName` = `Charlie Puth - Attention (Voicenotes)`：
            - `专辑艺人` = `Charlie Puth`
            - `名称` = `Attention`
            - `专辑名称` = `Voicenotes`
        - `Various Artists - Futile Devices (Doveman Remix) (Call Me By Your Name (Original Motion Picture Soundtrack))`：
            - `专辑艺人` = `Various Artists`
            - `名称` = `Futile Devices (Doveman Remix)`
            - `专辑名称` = `Call Me By Your Name (Original Motion Picture Soundtrack)`
        - `Glee Cast - Hello (Glee Cast Version) [feat. Jonathan Groff] (Glee: The Music, The Complete Season One)`：
            - `专辑艺人` = `Glee Cast`
            - `名称` = `Hello (Glee Cast Version) [feat. Jonathan Groff]`
            - `专辑名称` = `Glee: The Music, The Complete Season One`
2. 使用 API 获取用户所有音乐。
    - Curl 示例：
        ```bash
        curl -X 'GET' \
          '${URL}/Items?userId=${user_id}&recursive=true&includeItemTypes=Audio' \
          -H 'accept: application/json' \
          -H 'Authorization: MediaBrowser Client="${MEDIA_BROWSER_CLIENT}", Device="${DEVICE}", DeviceId="${device_id}", Version="${VERSION}", Token="{access_token}"'
        ```
    - 响应示例： @samples/response_items_audio.json 。
3. 通过 `Name`、`Album`、`AlbumArtist`（**注意**！是专辑艺人而不是艺人）获取项目 `Id`。
    - 错误处理：移除没有找到的项目（允许数量减少），并控制台警告。

### 提交列表

使用项目 `id`，逐周期构建播放列表并更新至 Jellyfin。

1. 构建请求体。示例：
    ```json
    {
      "Name": "{name}",
      "Ids": [
        "{id_0}",
        "{id_1}"
      ],
      "UserId": "{user_id}",
      "MediaType": "Audio",
      "Users": [],
      "IsPublic": {IS_PUBLIC}
    }
    ```
2. 使用 API 获取用户所有播放列表。
    - Curl 示例：
        ```bash
        curl -X 'GET' \
          '${URL}/Items?userId=${user_id}&recursive=true&includeItemTypes=playlist' \
          -H 'accept: application/json' \
          -H 'Authorization: MediaBrowser Client="${MEDIA_BROWSER_CLIENT}", Device="${DEVICE}", DeviceId="${device_id}", Version="${VERSION}", Token="{access_token}"'
        ```
    - 响应示例： @samples/response_items_playlist.json 。
3. 通过响应中的 `Name` 字段，查找待处理的播放列表名称是否存在。
    - 如果存在，带请求体更新播放列表。
        - Curl 示例：
            ```bash
            curl -X 'POST' \
              '${URL}/Playlists/${playlist_id}' \
              -H 'accept: */*' \
              -H 'Authorization: MediaBrowser Client="${MEDIA_BROWSER_CLIENT}", Device="${DEVICE}", DeviceId="${device_id}", Version="${VERSION}", Token="{access_token}"' \
              -H 'Content-Type: application/json' \
              -d '${request_body}'
            ```
        - 响应：`204`。
    - 如果不存在，带请求体创建播放列表。
        - Curl 示例：
            ```bash
            curl -X 'POST' \
              '${URL}/Playlists' \
              -H 'accept: application/json' \
              -H 'Authorization: MediaBrowser Client="${MEDIA_BROWSER_CLIENT}", Device="${DEVICE}", DeviceId="${device_id}", Version="${VERSION}", Token="{access_token}"' \
              -H 'Content-Type: application/json' \
              -d '${request_body}'
            ```
        - 响应示例：
            ```json
            {
              "Id": "045758b38bb0e36065f66b8b017119ff"
            }
            ```

## 周期

可配置禁用对应生成。播放列表名称和格式由环境变量配置，包含占位符。

### 划分规则

- 年：自然年
- 半年：
  | 编号 (`{half}`) | 自然月 |
  | ---- | --------- |
  | `1` | 1 - 6 月 30 日 |
  | `2` | 7 - 12 月 31 日 |
- 季度：
  | 编号 (`{quarter}`) | 自然月 |
  | ---- | ---------- |
  | `1` | 1 - 3 月 31 日 |
  | `2` | 4 - 6 月 30 日 |
  | `3` | 7 - 9 月 30 日 |
  | `4` | 10 - 12 月 31 日 |

### 占位符

| 占位符      | 类型  | 取值范围           | 示例                                                             |
| ----------- | ----- | ------------------ | ---------------------------------------------------------------- |
| `{year}`    | `int` | `r'\d{2}(\d{2})?'` | `2025` (`YEAR_FORMAT` == `'%Y'`)、`25` (`YEAR_FORMAT` == `'%y'`) |
| `{half}`    | `int` | in `[1, 2]`        |
| `{quarter}` | `int` | in `[1, 2, 3, 4]`  |

### 名称配置示例

- 年：
    - `YEAR_FORMAT` = `'%Y'`
    - `YEAR_REPLAY_TITLE_TEMPLATE` = `'Replay {year}'`
    - 播放列表名称：
        ```text
        Replay 2024
        Replay 2025
        Replay 2026
        ```
- 半年：
    - `YEAR_FORMAT` = `'%y'`
    - `HALF_REPLAY_TITLE_TEMPLATE` = `'Replay {year}H{half} '`
    - 播放列表名称：
        ```text
        Replay 24H2
        Replay 25H1
        ```
- 季度：
    - `YEAR_FORMAT` = `'%Y'`
    - `QUARTER_REPLAY_TITLE_TEMPLATE` = `'Replay Q{quarter} {year}'`
    - 播放列表名称：
        ```text
        Replay Q3 2025
        Replay Q4 2025
        Replay Q1 2026
        ```
