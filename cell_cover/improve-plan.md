/act
我们将分阶段实施这些需求：
阶段一：核心功能重构 (R1, R2, R5)
修改 generate_prompt_text: 使其返回一个字典，包含 prompt 字符串以及从配置和参数解析出的 aspect, quality, model (对应 version) 等独立字段。
修改 call_imagine_api:
接收参数字典。
构造符合 ttapi.md 规范的 JSON 请求体。
增加 hookUrl 和 notify_id 参数，并包含在请求体中。
移除轮询: 删除 poll_for_result 函数及 main 函数中相关的调用和等待逻辑。
修改 main 函数:
添加 --hook-url (必需) 和 --notify-id (可选) 命令行参数。
调用修改后的 call_imagine_api 提交任务。
更新输出信息，告知用户任务已提交，结果将发送至 Webhook。
清理 utils 依赖: 评估 utils 中的 image.download_and_save_image 和元数据保存逻辑。将必要的下载和元数据保存逻辑（目前脚本中已有fallback实现）整合到 generate_cover.py 中，移除 try-except ImportError 和对 utils 的调用尝试。
阶段二：健壮性增强 (R3, R4)
引入 logging: 配置基本的日志记录器，替换所有 print 语句。
增强错误处理:
在 call_imagine_api 中捕获 requests 异常。
检查 TTAPI 返回的 status 和 message，记录更详细的错误日志。
为 API 调用增加简单的重试逻辑（例如，重试 1 次，间隔 2 秒）。
阶段三：可选功能与完善 (R6, R7, R8)
实现 /promptCheck (可选):
添加 call_prompt_check_api 函数。
添加 --check-prompt 命令行参数。
在 main 中根据参数决定是否调用检查。
扩展参数支持 (可选):
根据需要，为 /imagine 的其他参数（如 translation, getUImages, 自定义 timeout）添加命令行参数，并在 call_imagine_api 中处理。
更新帮助文档: 修改 argparse 的描述和参数说明，反映所有更改。