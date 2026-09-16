# Talkami Pinyin Audio

Talkami 小程序的汉语拼读音频仓库。

这个仓库只放拼音音频的发布配置和 manifest。实际音频使用 GitHub Releases 保存，不把约 120MB 音频重复提交进 Git 历史。

## 当前发布方案

- 仓库：`hurt56631-ui/talkami-pinyin-audio`
- 仓库保持 Public
- 默认音频总数：1338
- 默认分 3 个 Release，每批建议 446 个
- 小程序读取：`manifest/latest.json`
- 用户可在小程序中一次性下载完整离线包；中断后按 manifest 继续下载未完成文件

Release 标签：

```text
pinyin-audio-v1-part1
pinyin-audio-v1-part2
pinyin-audio-v1-part3
```

## 第一次上传音频

### 1. 自动创建 3 个 Release

进入 GitHub：

`Actions` → `Prepare and publish Pinyin audio` → `Run workflow`

填写：

```text
action: prepare_releases
version: 1
part_count: 3
expected_count: 1338
```

工作流会自动创建 3 个空 Release。

### 2. 上传音频

进入 `Releases`，分别打开：

```text
pinyin-audio-v1-part1
pinyin-audio-v1-part2
pinyin-audio-v1-part3
```

把音频文件直接拖进去上传，不要打 ZIP。

1338 个文件正好可以按下面分：

```text
part1: 446
part2: 446
part3: 446
```

也可以用其他分法，只要：

- 三批总数等于 1338
- 每一批不要超过 900 个文件
- 三个 Release 中不能出现同名音频

推荐文件名只使用：

```text
A-Z a-z 0-9 - _ .
```

例如：

```text
ba1.mp3
ba2.mp3
bai3.mp3
zhong1.mp3
guo2.mp3
```

尽量不要使用空格、`#`、中文括号等特殊字符。GitHub 上传 Release asset 时可能自动改写特殊文件名。

### 3. 上传完成后生成 manifest

再次运行同一个 Action：

```text
action: build_manifest
version: 1
part_count: 3
expected_count: 1338
```

工作流会自动：

1. 读取 3 个 Release 的全部 asset（支持每批超过 100 个，自动分页）
2. 校验三批总数
3. 检查重复文件名和不支持的文件类型
4. 收集 GitHub 提供的 SHA-256 digest（可用时）
5. 统计每个文件和全部资源的大小
6. 生成 `manifest/pinyin-v1.json`
7. 同步更新 `manifest/latest.json`
8. 自动提交 manifest 到 `main`

## manifest 给小程序的数据

每个音频条目会包含类似：

```json
{
  "id": "part1:ba1.mp3",
  "name": "ba1.mp3",
  "part": 1,
  "size": 84231,
  "digest": "sha256:...",
  "download_url": "https://github.com/hurt56631-ui/talkami-pinyin-audio/releases/download/pinyin-audio-v1-part1/ba1.mp3"
}
```

小程序不需要知道用户正在下载第几个 Release，只按 manifest 的 `items` 顺序下载、保存和续传即可。

## 更新音频

已经发布给用户的 v1 不要覆盖。

如果以后修改或增加音频，使用新的版本，例如：

```text
pinyin-audio-v2-part1
pinyin-audio-v2-part2
pinyin-audio-v2-part3
```

然后运行 `build_manifest`，`manifest/latest.json` 会切换到 v2。这样已经缓存 v1 的用户不会因为同 URL 内容变化而出现脏缓存。

## 支持的音频扩展名

```text
.mp3 .m4a .aac .wav .ogg .opus
```

生产环境建议优先使用 MP3 或 AAC/M4A，以获得较好的 Telegram Android/iOS WebView 兼容性。
