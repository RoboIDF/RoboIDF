# 论文写作与编译

`manuscript.md` 是本地写作主源，引用来自 `references.bib`。`main.tex` 是可独立在 Overleaf 编辑/编译的导出源码；不要同时修改两份正文。

```bash
pixi install --locked
pixi run --locked paper-build
pixi run --locked paper-check
```

构建使用锁定的 Pandoc + Tectonic，生成 main.tex、main.pdf 和 overleaf.zip。Tectonic 首次运行需要联网下载其 TeX bundle 与 Fandol 中文字体；Pixi 锁文件固定工具版本，但不包含下载缓存。CI 也需网络。当前中文单栏初稿，未套用会议模板。

引用由 Pandoc citeproc 从 BibTeX 解析并写入 LaTeX，Overleaf 不需要额外运行 Biber。Overleaf 上传 overleaf.zip 后选择 main.tex 和 XeLaTeX；仅同步打包文件，不上传仓库其他代码或凭据。

原 papers/ 目录中的 Markdown 是 v0.1 历史初稿，后续在此目录维护正文。Overleaf 修改必须先取回、审查并合并到主源再重新生成，不能盲目覆盖。禁止强推或自动双向同步。

## 研究工作流

1. 文献：核对原始来源，记录引用和支持范围，不将背景资料当作本项目实验结果。
2. 写作：区分拟议设计、实现证据与实测结论；保留当前尚无实验结果的说明。
3. 实验：只用真实日志生成指标，记录版本、种子、划分及失败。
4. 审阅：检查推理、引用、单位、可复现性；编译后查看公式、表格及参考文献页面。
5. 发布：审查 diff，提交源码、BibTeX、PDF 和导入包；GitHub 为版本主库，Overleaf 为协作镜像。

## 验证记录（2026-11-01）

本地 `paper-build` 与 `paper-check` 已通过，已检查全部页面排版；检查使用 Pixi 锁定的 PyMuPDF 提取中文。结果仍为无实验数据的设计/协议初稿。

## Overleaf 状态

项目：https://www.overleaf.com/project/6ae7075bab7573986e2ab6db 。用户已确认名称为 RoboIDF。浏览器控制连接超时，尚未导入源码、验证在线编译或配置 Git 同步；不得视为已经接入。Git token 不是网页登录凭据，任何 token 不得存入仓库或聊天。

## GitHub 自动编译

配置位于 `.github/workflows/paper.yml`，在论文、脚本或环境文件变更时编译并检查，保留 PDF、LaTeX 与 Overleaf ZIP 产物；也可手动触发。目前正在完成 workflow 授权，尚未推送并验证远程执行。
