# tv — IPTV 直播源镜像

把直播源地址写进仓库，GitHub Actions 定时下载并 **原样镜像**（逐字节一致，不解析、不去重、不改格式），通过 raw / 加速链接给播放器订阅。

## 订阅地址（live.m3u）

| 线路 | 链接 |
|------|------|
| GitHub Raw | https://raw.githubusercontent.com/baogj/tv/main/output/live.m3u |
| jsDelivr | https://cdn.jsdelivr.net/gh/baogj/tv@main/output/live.m3u |
| jsDelivr Fastly | https://fastly.jsdelivr.net/gh/baogj/tv@main/output/live.m3u |
| gh-proxy | https://gh-proxy.com/https://raw.githubusercontent.com/baogj/tv/main/output/live.m3u |
| ghfast | https://ghfast.top/https://raw.githubusercontent.com/baogj/tv/main/output/live.m3u |

> jsDelivr 有缓存，更新可能延迟数小时；需要最新内容时优先用 Raw / gh-proxy / ghfast。

## 如何添加源

1. 编辑 [`config/sources.txt`](config/sources.txt)，每行一个 URL；`#` 开头为注释，空行忽略
2. 第 1 个源保存为 `output/live.m3u`，第 2 个为 `output/source2.m3u`，第 3 个为 `output/source3.m3u`，依此类推（各自独立，不合并）
3. 提交并推送到 `main`，或手动触发工作流

## 如何更新

- 自动：每 **6 小时** 一次（cron `0 */6 * * *`）；修改 `config/`、`scripts/` 或工作流后推送到 `main` 也会触发
- 手动：[Actions → Update IPTV sources](https://github.com/baogj/tv/actions/workflows/update.yml) → **Run workflow**
- 本地：`python3 scripts/update.py`

## 说明

- 输出文件与源站返回内容 **逐字节一致**（不解码、不转换换行、不改头部）；`.gitattributes` 中 `output/* -text` 防止 Git 转换换行
- 仅在 HTTP 200 且内容非空时覆盖；下载失败会保留上一次的文件
- 本仓库仅镜像公开链接，不托管视频内容；请遵守当地法律法规及源站条款
