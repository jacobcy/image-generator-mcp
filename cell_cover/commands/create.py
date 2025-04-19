# -*- coding: utf-8 -*-
import os
import logging
import uuid
from datetime import datetime
# 导入 sys 用于刷新缓冲区
import sys

# 从 utils 导入必要的函数
# Corrected import: Functions are in api_client.py, not ttapi_client.py, and names are different
from ..utils.api_client import call_imagine_api, poll_for_result
from ..utils.prompt import generate_prompt_text, save_text_prompt, copy_to_clipboard, PYPERCLIP_AVAILABLE
from ..utils.file_handler import download_and_save_image, save_image_metadata
from ..utils.image_uploader import process_cref_image
# 修正导入，check_prompt 在 api_client 中
from ..utils.api_client import check_prompt

logger = logging.getLogger(__name__)

def handle_create(args, config, logger, api_key):
    """处理 'create' 命令。"""
    # --- 1. 处理参考图片 (Cref) ---
    cref_url = None
    if args.cref:
        # process_cref_image handles logging and printing errors
        cref_url = process_cref_image(logger, args.cref)
        if not cref_url:
            return 1 # Exit if cref processing failed
        else:
            logger.info(f"使用处理后的 Cref URL: {cref_url}")

    # --- 2. 生成提示词 ---
    prompt_result = None # 重命名以区分字典和字符串
    concept_key_for_save = None
    logger.debug("开始生成提示词...")
    if args.concept:
        prompt_result = generate_prompt_text(
            logger, config, args.concept, args.variation, args.style,
            args.aspect, args.quality, args.version, cref_url
        )
        concept_key_for_save = args.concept
        logger.debug(f"generate_prompt_text 返回: {type(prompt_result)}")
    elif args.prompt:
        # Direct prompt handling might need parameter appending logic similar to generate.py
        # For now, assume it includes necessary params or handle_create needs adjustment
        prompt_result = args.prompt # 直接使用字符串
        logger.debug("直接使用用户提供的 prompt 字符串")
        # TODO: Add parameter appending logic if needed for direct prompts in create
    else:
        logger.error("使用 'create' 命令时，必须提供 --concept 或 --prompt 参数。")
        print("错误：使用 'create' 命令时，必须提供 --concept 或 --prompt 参数。")
        return 1

    # 检查 generate_prompt_text 的返回值或用户输入
    if not prompt_result:
        logger.error("无法生成或获取提示词文本。")
        print("错误：无法生成或获取提示词文本。")
        return 1 # 如果 prompt_result 为空或 None，程序退出

    # --- 提取提示词字符串 ---
    # generate_prompt_text 返回字典，直接输入是字符串
    if isinstance(prompt_result, dict):
        prompt_str = prompt_result.get("prompt", "")
        if not prompt_str:
             logger.error("生成的提示词结果字典中缺少 'prompt' 键或值为空。")
             print("错误：生成的提示词结果无效。")
             return 1
    elif isinstance(prompt_result, str):
        prompt_str = prompt_result
    else:
        logger.error(f"获取到的提示词类型未知: {type(prompt_result)}。")
        print("错误：获取到的提示词类型无效。")
        return 1

    logger.debug("成功获取提示词字符串。")

    # 检查版本与 cref 的兼容性 (现在使用 prompt_str)
    if cref_url and ("--v 6" not in prompt_str and "--v 7" not in prompt_str):
        logger.warning("警告：--cref 参数通常与 Midjourney v6 或 v7 一起使用。")
        print("警告：--cref 参数通常与 Midjourney v6 或 v7 一起使用。")

    logger.info(f"最终使用的提示词: {prompt_str}")
    print(f'''Generated Prompt:\\n---\\n{prompt_str}\\n---''')

    if args.clipboard:
        if PYPERCLIP_AVAILABLE:
            logger.debug("尝试复制到剪贴板...")
            try:
                copy_to_clipboard(logger, prompt_str) # 使用 prompt_str
                logger.info("提示词已复制到剪贴板。")
                logger.debug("复制到剪贴板完成。")
            except Exception as e:
                logger.error(f"复制到剪贴板时出错: {e}", exc_info=True)
                print(f"警告：复制到剪贴板失败 - {e}")
        else:
            logger.warning("警告：Pyperclip 模块不可用，无法复制到剪贴板。")
            print("警告：Pyperclip 模块不可用，无法复制到剪贴板。")
    if args.save_prompt:
        # 使用 OUTPUT_DIR 作为输出目录
        from ..utils.file_handler import OUTPUT_DIR
        # filename_base = concept_key_for_save if concept_key_for_save else f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        # 使用更可靠的文件名基础，即使没有 concept_key
        filename_base = concept_key_for_save if concept_key_for_save else "custom_prompt"
        logger.debug("尝试保存提示词文件...")
        try:
            save_text_prompt(logger, OUTPUT_DIR, prompt_str, filename_base) # 使用 prompt_str
            logger.debug("保存提示词文件完成。")
        except Exception as e:
             logger.error(f"保存提示词文件时出错: {e}", exc_info=True)
             print(f"错误：保存提示词文件失败 - {e}")
             # Decide if this error is critical enough to stop
             # return 1


    # --- 3. 检查提示词安全 ---
    logger.info("正在检查提示词安全性...")
    logger.debug(f"准备调用 check_prompt，API Key: {'***' if api_key else 'None'}") # 修正 API Key 变量名
    try:
        # 直接使用提取出的 prompt_str
        is_safe = check_prompt(logger, prompt_str, api_key)
        logger.debug(f"check_prompt 返回: {is_safe}")

        if not is_safe:
            # 错误消息已由 check_prompt 打印，这里仅记录并退出
            logger.error("提示词安全检查未通过或检查过程中发生错误。退出。")
            # 确保之前的 print 语句被刷新
            sys.stdout.flush()
            sys.stderr.flush()
            return 1 # 明确退出
        else:
            logger.info("提示词安全检查通过。")

    except Exception as e:
        # 捕获调用 check_prompt 本身可能发生的意外（理论上不应发生，因为内部已处理）
        logger.critical(f"调用 check_prompt 时发生未预料的严重错误: {e}", exc_info=True)
        print(f"严重错误：调用提示词安全检查时失败: {e}")
        sys.stdout.flush()
        sys.stderr.flush()
        return 1 # 发生严重错误也退出


    # --- 4. 提交任务到 API ---
    # 确保我们使用正确的提示词字符串 (prompt_str)
    # prompt_str = prompt_text["prompt"] if isinstance(prompt_text, dict) else prompt_text # 不再需要，已提前处理
    prompt_data = {"prompt": prompt_str, "mode": args.mode} # 使用 prompt_str
    logger.info(f"准备提交任务到 TTAPI (模式: {args.mode})...")
    print(f"正在提交任务 (模式: {args.mode})...")

    # Use the corrected function name call_imagine_api
    # 注意：我们不需要再次传递 cref_url，因为它已经包含在 prompt_str 中了 (由 generate_prompt_text 添加)
    logger.debug(f"调用 call_imagine_api...")
    submit_result = call_imagine_api(
        logger, prompt_data, api_key,
        hook_url=args.hook_url,
        notify_id=args.notify_id
        # 注意：不再需要传递 cref_url 参数给 call_imagine_api
        # 因为 generate_prompt_text 已经将其加入了 prompt_str
        # 而 api_client.call_imagine_api 也不接受独立的 cref_url 参数
    )
    logger.debug(f"call_imagine_api 返回: {submit_result}")

    if submit_result:
        job_id = submit_result
        logger.info(f"任务提交成功，Job ID: {job_id}")
        job_id_for_save = job_id
        # 保存原始的 prompt_result 或提取的 prompt_str？ 保存字符串更简单
        prompt_text_for_save = prompt_str
        seed_for_save = None # Seed is unknown until task completes

        # --- 5. 处理结果 (轮询或 Webhook) ---
        if not args.hook_url:
            logger.info("未提供 Webhook URL，将开始轮询结果...")
            print("Polling for result...")
            # Use the corrected function name poll_for_result
            logger.debug(f"调用 poll_for_result for job ID: {job_id}...")
            final_result = poll_for_result(logger, job_id, api_key)
            logger.debug(f"poll_for_result 返回: {type(final_result)}")

            if final_result and (final_result.get("image_url") or final_result.get("cdnImage")):
                image_url = final_result.get("image_url") or final_result.get("cdnImage")
                logger.info(f"任务完成，图像 URL: {image_url}")

                # --- 6. 下载并保存结果 ---
                logger.debug("准备下载并保存图像...")
                download_success, saved_path, image_seed = download_and_save_image(
                    logger, image_url, job_id, prompt_text_for_save, concept_key_for_save,
                    args.variation, args.style, None, # original_job_id
                    None, # action_code
                    final_result.get("components"),
                    final_result.get("seed")
                )
                logger.debug(f"download_and_save_image 返回: success={download_success}, path={saved_path}, seed={image_seed}")
                if download_success:
                    seed_for_save = image_seed # Use seed from download if available
                    # 使用更安全的 job_id
                    if job_id_for_save:
                        save_image_metadata(
                            logger, final_result.get("image_id", str(uuid.uuid4())),
                            job_id_for_save, os.path.basename(saved_path), saved_path,
                            image_url, prompt_text_for_save, concept_key_for_save,
                            args.variation, args.style,
                            final_result.get("components"), seed_for_save, None # original_job_id
                        )
                        logger.info(f"图像和元数据已保存: {saved_path}")
                        print(f"图像和元数据已保存: {saved_path}")
                        return 0
                    else:
                        logger.error("内部错误: job_id_for_save 为空，无法保存元数据。")
                        print("错误：内部错误，无法保存元数据。")
                        return 1
                else:
                    logger.error("图像下载或保存失败。")
                    print("错误：图像下载或保存失败。")
                    return 1
            else:
                status = final_result.get('status') if isinstance(final_result, dict) else 'N/A' # 更安全的检查
                error_msg = f"轮询任务结果失败或未获取到图像 URL。最后状态: {status}"
                logger.error(error_msg)
                print(f"错误：{error_msg}")
                if job_id_for_save: # Save basic metadata even on failure
                     save_image_metadata(
                          logger, None, job_id_for_save, None, None, None,
                          prompt_text_for_save, concept_key_for_save, args.variation, args.style,
                          final_result, seed_for_save, None
                     )
                     logger.info(f"已保存任务 {job_id_for_save} 的基本元数据（无图像）。")
                return 1
        else: # Webhook provided
            logger.info("提供了 Webhook URL，任务将在后台处理。")
            print("提供了 Webhook URL，任务将在后台处理。")
            # Save initial metadata
            if job_id_for_save:
                save_image_metadata(
                    logger, None, job_id_for_save, None, None, None,
                    prompt_text_for_save, concept_key_for_save, args.variation, args.style,
                    {"jobId": job_id_for_save, "status": "SUBMITTED_WITH_WEBHOOK"}, # 修正 submit_result 可能是字符串的问题
                    seed_for_save, None
                )
                logger.info(f"已保存任务 {job_id_for_save} 的初始元数据（无图像）。")
                return 0
            else:
                 logger.error("内部错误: 任务提交成功但 job_id_for_save 为空 (Webhook 场景)。")
                 print("错误：内部错误，无法保存任务初始元数据。")
                 return 1
    else: # Submit failed
        error_msg = "任务提交失败 (API 调用未返回 Job ID)"
        logger.error(error_msg)
        print(f"错误：{error_msg}")
        return 1

# 可以在文件末尾添加一个 main guard 用于测试 (如果需要)
# if __name__ == '__main__':
#     pass
