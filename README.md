# tv — IPTV 直播源聚合

把多个直播源地址写进仓库，GitHub Actions 定时抓取、去重、合并，通过 **raw** 链接给播放器订阅。

## 订阅地址

| 格式 | 链接 |
|------|------|
| M3U | https://raw.githubusercontent.com/baogj/tv/main/output/live.m3u |
| TXT（频道名,地址） | https://raw.githubusercontent.com/baogj/tv/main/output/live.txt |

jsDelivr CDN（国内有时更稳）：

- https://cdn.jsdelivr.net/gh/baogj/tv@main/output/live.m3u
- https://cdn.jsdelivr.net/gh/baogj/tv@main/output/live.txt

把上面任一地址粘贴到支持直播列表的播放器即可（如 TiviMate、IPTV Smarters、影视仓、OK 影视等）。

## 如何添加源

1. 编辑 [`config/sources.txt`](config/sources.txt)
2. 每行一个直播源 URL（支持 M3U / M3U8 播放列表，或 `频道名,地址` 的 TXT）
3. `#` 开头为注释，空行忽略
4. 提交并推送到 `main` 分支，或手动触发工作流

仓库里预置了若干 **示例源**（iptv-org 公开列表），可随时删掉换成你自己的。

## 如何更新

自动：

- 每 **6 小时** 跑一次（cron `0 */6 * * *`）
- 修改 `config/`、`scripts/` 或本工作流后推送到 `main` 也会触发

手动：

1. 打开 [Actions → Update IPTV sources](https://github.com/baogj/tv/actions/workflows/update.yml)
2. 点击 **Run workflow**

本地调试：

```bash
python3 scripts/update.py
```

会生成 / 覆盖 `output/live.m3u` 与 `output/live.txt`。单个源失败不会中断整次合并。

## 说明

- 脚本仅聚合公开链接，不托管视频内容
- 去重键为流地址 URL，同地址保留第一次出现的频道名
- 请遵守当地法律法规与源站使用条款；失效源请自行替换
