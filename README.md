# Talkami 拼读音频库

这个仓库只负责 **汉语拼读 / 完整音节训练**，不再承担“基础拼音”资源。

> 重要：`a / o / e`、声母、韵母、整体认读、声调教学属于“拼音基础”；新的基础拼音仓库单独维护。这里保留 1338 个现有 WAV，作为拼读/音节训练资源库。

## 当前资源

v1 已完成：

```text
pinyin-audio-v1-part1   477 个
pinyin-audio-v1-part2   428 个
pinyin-audio-v1-part3   433 个
--------------------------------
总计                    1338 个
```

最终离线 Release：

```text
pinyin-v1
├─ pinyin-v1-part1.zip
├─ pinyin-v1-part2.zip
├─ pinyin-v1-part3.zip
└─ pinyin-manifest-v1.json
```

GitHub Actions 已完成“源 Release -> 校验 -> 分包 ZIP -> manifest -> 最终 Release”的发布流程。

## 小程序用途

这个仓库用于“拼读/音节训练”，例如：

```text
b + a -> ba
m + ao -> mao
zh + uang -> zhuang

ba1.wav
ba2.wav
ba3.wav
ba4.wav
```

小程序完整离线下载时读取：

```text
manifest/latest.json
```

然后按 `packages` 顺序下载 ZIP、逐包解压到 IndexedDB。未下载时仍可根据 manifest 中的 `stream_url` 在线播放。

## 不属于本仓库的内容

下面这些内容将放到新的 **基础拼音仓库**：

```text
声母：b p m f d t n l ...
韵母：a o e i u ü ai ei ao ou ...
整体认读：zhi chi shi ri zi ci si yi wu yu ...
声调：一声 / 二声 / 三声 / 四声及示范音
```

基础拼音和拼读从仓库、manifest、Release 到小程序页面全部分开，避免资源和教学逻辑混用。
