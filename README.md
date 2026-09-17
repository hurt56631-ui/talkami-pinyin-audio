# Talkami Pinyin Audio

Talkami 小程序的汉语拼读音频仓库。

## 架构

这个仓库现在采用“源资源 -> GitHub Actions 构建 -> 最终 Release 下载”的方式，和 `talkami-learning-content` 的发布思路一致。

区别只在源资源存放位置：

- `talkami-learning-content` 的源 JSON/封面等主要放在 Git 项目文件中，再构建 `dist/`。
- 拼音共有 1338 个 WAV、约 120MB。为了不把大量二进制长期堆进 Git 历史，原始音频放在 3 个“上传区 Release”。
- GitHub Actions 会把上传区音频全部拉到 runner，校验后打成 ZIP，最后发布一个真正给小程序下载的 `pinyin-vN` Release。
- Git 仓库只保存 workflow、构建脚本和 manifest。

所以用户不会下载 1338 个 Release 附件；用户只下载最终打包结果。

## v1 当前上传状态

已经上传完成：

```text
pinyin-audio-v1-part1   477 个
pinyin-audio-v1-part2   428 个
pinyin-audio-v1-part3   433 个
--------------------------------
总计                    1338 个
```

三批数量不需要相同，只要总数和文件校验通过即可。

## 上传区和最终下载区

### 源音频上传区

```text
pinyin-audio-v1-part1
pinyin-audio-v1-part2
pinyin-audio-v1-part3
```

这里保存原始 WAV。它们是构建输入，不是小程序完整离线包。

### 最终 Release

运行 Action 后自动创建：

```text
pinyin-v1
```

里面会有：

```text
pinyin-v1-part1.zip
pinyin-v1-part2.zip
pinyin-v1-part3.zip
pinyin-manifest-v1.json
```

每个 ZIP 对应一批源音频。Action 会计算每个音频和每个 ZIP 的 SHA-256、文件数、原始大小、压缩后大小，并写进 manifest。

## 现在怎么发布 v1

进入：

`Actions` -> `Prepare and publish Pinyin audio` -> `Run workflow`

填写：

```text
action: build_and_publish
version: 1
part_count: 3
expected_count: 1338
```

工作流会自动：

1. 下载三个上传区 Release 的全部音频。
2. 检查三批总数是否等于 1338。
3. 检查跨批重复文件名、空文件和不支持格式。
4. 对每个音频计算 SHA-256。
5. 分别生成 3 个 ZIP。
6. 对 3 个 ZIP 再计算 SHA-256 和大小。
7. 生成 `manifest/pinyin-v1.json` 和 `manifest/latest.json`。
8. 创建最终 Release `pinyin-v1`，上传 3 个 ZIP + manifest。
9. 把最终 manifest 提交回 `main`。

## 小程序使用方式

小程序只读取：

```text
manifest/latest.json
```

完整离线下载时按照 manifest 的 `packages` 顺序下载：

```text
part1.zip -> 解压并写 IndexedDB -> 标记 part1 完成
part2.zip -> 解压并写 IndexedDB -> 标记 part2 完成
part3.zip -> 解压并写 IndexedDB -> 标记 part3 完成
```

这样如果用户完成 part1 后关闭 Telegram，下次从 part2 继续，不需要重新下载 part1。

manifest 还保留每条音频的 `stream_url`，所以未下载完整离线包时也可以按单个音频在线播放。

## 以后更新

v1 发布后不要覆盖。

修改或增加音频时创建新的上传区：

```text
pinyin-audio-v2-part1
pinyin-audio-v2-part2
pinyin-audio-v2-part3
```

再运行：

```text
action: build_and_publish
version: 2
```

最终生成新的 `pinyin-v2`，`manifest/latest.json` 再切换到 v2。

## 支持格式

```text
.mp3 .m4a .aac .wav .ogg .opus
```

当前 v1 上传的是 WAV。ZIP 会在 GitHub Actions 中自动生成，无需再次手工上传 ZIP，也无需重新上传现有 1338 个音频。
