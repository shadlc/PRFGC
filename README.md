# python robot for go-cqhttp

## Description
一个适用于Linux和Windows理论支持Mac，用于对接[go-cqhttp](https://github.com/Mrs4s/go-cqhttp)进行处理的python程序

## Usage
- 安装Python3.7或以上
- 使用pip install -r requirements.txt安装程序所需第三方库
- Windows用户请额外执行 pip install windows-curses
- 酌情启动"start.bat"或者"start.sh"

## Tips
- 该项目主要功能请在后台使用help指令查看
- 模块化添加删除需要功能请添加文件至文件夹function，并在execute.py中添加，模块格式参考message.py
- 默认对接的cqhttpHTTP监听地址为"127.0.0.1:5700"，反向HTTP POST地址为"127.0.0.1:5701"，可自行修改config.ini进行调整
- 使用Windows自带的命令提示符无法支持颜色效果,因此Windows默认关闭颜色代码，编辑print_color.py开启
- 模块错误默认采用ifunction.py中simplify_traceback()函数处理，便于debug
- 该项目为轻量化使用未采用curses图形库而采用多线程处理后台IO，因此输入命令时收到的新消息可能覆盖命令的显示

## Features
- 模块化的功能加入
- 基础的类终端交互
- 清晰的界面显示和排版
- Threading多线程处理消息
- 方便的调试接口和错误提示
- 每个群和用户的独立数据存储
- 方便快捷的随机文本选择和回复
- 对图片信息的终端彩色像素画显示
- 支持大部分常用go-cqhttp接口调用
