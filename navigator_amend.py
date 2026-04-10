import logging
import re
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
import pyautogui
import time

def execute_amend_flow(software_name: str, applicant_type: str, wait_callback, captcha_callback, page_judger, logger=print) -> bool:
    """
    Connects to an existing Edge browser on port 9222 and performs
    precise navigation and clicking for the software amend registration using Playwright.
    """
    with sync_playwright() as p:
        try:
            logger("正在通过 CDP (端口9222) 连接至 Edge 浏览器...")
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            
            context = browser.contexts[0]
            target_page = None
            
            for page in context.pages:
                if "register.ccopyright" in page.url or "register.html" in page.url or "account.html" in page.url:
                    if target_page is None:
                        target_page = page
                    else:
                        try:
                            page.close()
                        except Exception:
                            pass
                elif "newtab" in page.url or page.url == "about:blank":
                    try:
                        page.close()
                    except Exception:
                        pass
            
            if not target_page:
                logger("❌ 未能在浏览器中找到版权登记官网标签页。")
                return False

            target_page.bring_to_front()
            logger("✅ 成功接管版权官网页面，开始补正流程操作...")

            def smart_wait(delay_ms):
                """智能等待：期间检测鼠标是否大幅晃动，若是则触发暂停"""
                start_time = time.time() * 1000
                last_pos = pyautogui.position()
                
                while time.time() * 1000 - start_time < delay_ms:
                    target_page.wait_for_timeout(100)
                    curr_pos = pyautogui.position()
                    dist = ((curr_pos[0] - last_pos[0])**2 + (curr_pos[1] - last_pos[1])**2)**0.5
                    if dist > 200: # 晃动阈值
                        logger("【动作中断】检测到明显的鼠标晃动，触发人工接管保护机制！")
                        logger("====== ⏸ 自动化已暂停 ======")
                        wait_callback(msg="检测到您的鼠标晃动打断了流程。\n您现在可以在网页上进行人工浏览、修改或上传文件。\n\n处理完成后，请点击界面的【继续】按钮恢复自动化操作。")
                        logger("====== ▶ 继续 ======")
                        # 中断处理完后重置基准坐标，避免立即由于刚才甩鼠标的位移引发连环中断
                        last_pos = pyautogui.position()
                    else:
                        last_pos = curr_pos

            # 1. 导航到“待补正”选项卡

            nav_xpath = "/html/body/div[2]/div[2]/div/div[2]/div[2]/div[1]/ul/li[6]/div[2]/span"
            logger(f"点击【待补正】选项卡: {nav_xpath}")
            try:
                target_page.locator(f"xpath={nav_xpath}").click(timeout=10000)
            except Exception as e:
                logger(f"⚠️ 无法通过 XPath 点到待补正，尝试文本点击: {e}")
                target_page.locator("li").filter(has_text=re.compile(r"待补正")).first.click()
                
            smart_wait(3000)

            # 2. 寻找对应的软件名称，并点击“去补正”按钮
            logger(f"正在智能寻找软件名称为 '{software_name}' 的【去补正】按钮...")
            try:
                row_locator = target_page.locator(f"xpath=//li[contains(., '{software_name}')] | //tr[contains(., '{software_name}')]")
                if row_locator.count() > 0:
                     btn = row_locator.first.locator("button, span.el-button").filter(has_text="去补正").first
                     if btn.count() > 0:
                          logger("✅ 成功通过关联匹配找到目标【去补正】按钮！按下...")
                          btn.click(timeout=5000)
                     else:
                          logger("⚠️ 未能在匹配行找到去补正按钮，降级全局搜索去补正...")
                          target_page.locator("button").filter(has_text=re.compile("去补正")).first.click(timeout=5000)
                else:
                    logger(f"⚠️ 未在列表中扫描到字样 '{software_name}' ，降级全局搜索去补正。")
                    target_page.locator("button").filter(has_text=re.compile("去补正")).first.click(timeout=5000)
            except Exception as e:
                logger(f"⚠️ 寻找去补正按钮产生异常: {e}，再次回退尝试盲点...")
                target_page.locator("button").filter(has_text=re.compile("去补正")).first.click(timeout=5000)
                
            smart_wait(3000)
            
            # 3. 补正流程界面前置依次点击
            logger(f"申请人类别选择为: {'代理申请' if applicant_type == 'proxy' else '自己申请'}")
            
            # 使用懒加载的语义 Locator
            first_loc = target_page.locator("xpath=(//div[contains(text(), '代理申请') or contains(text(), '代理他人')])[last()]") if applicant_type == "proxy" else target_page.locator("xpath=(//div[contains(text(), '自己申请') or contains(text(), '作为著作权人')])[last()]")
            next_btn_loc = target_page.locator("xpath=(//button[contains(text(), '下一步') or contains(text(), '确认')])[last()] | //button[contains(@class, 'primary') and not(contains(text(), '返回'))]").last
            gen_materials_loc = target_page.locator("xpath=(//button[contains(text(), '生成') or contains(text(), '确认') or contains(text(), '提取')])[last()] | //div[contains(text(), '确认')]").last
            
            clicks = [
                first_loc,
                next_btn_loc,
                next_btn_loc,
                gen_materials_loc
            ]
            
            logger("开始执行自动提交流程的深层菜单步进...")
            for index, loc in enumerate(clicks):
                logger(f"正在进行自动化前进操作 [{index + 1}/{len(clicks)}]...")
                try:
                    loc.wait_for(state="visible", timeout=10000)
                    loc.scroll_into_view_if_needed()
                    smart_wait(500)
                    loc.click(timeout=8000)
                except Exception as e:
                    logger(f"⚠️ 第 {index + 1} 步点击可能发生了偏移或无需点击 (跳过): {e}")
                smart_wait(2000)
            
            logger("✅ 已自动推进到达发证文档上传页面。")
            logger("====== ⏸ 暂停 ======")
            logger("请在弹出的程序界面点击【已手动上传，继续完成提交】！")
            
            # 4. 等待用户完成手动上传
            wait_callback()
            
            logger("====== ▶ 继续 ======")
            logger("用户确认完成，继续执行后续步骤...")
            
            post_upload_elem_1 = target_page.locator("xpath=(//button[contains(text(), '下一步') or contains(text(), '提交')])[last()] | //button[contains(@class, 'primary')]").last
            post_upload_elem_1.scroll_into_view_if_needed()
            smart_wait(500)
            post_upload_elem_1.click(timeout=10000)
            smart_wait(2000)
            
            post_upload_elem_2 = target_page.locator("xpath=(//span[contains(text(), '获取验证码')]) | //button[contains(text(), '获取')] | //a[contains(text(), '验证码')]").last
            post_upload_elem_2.scroll_into_view_if_needed()
            smart_wait(500)
            post_upload_elem_2.click(timeout=10000)
            smart_wait(3000)
            
            logger("准备进行系统安全滑块验证...")
            if page_judger:
                page_judger.solve_slider_captcha()
                
            logger("已尝试自动过滑块，接下来请您查收并【在网页上填写】短信验证码...")
            logger("💡 程序将自动监测填写状态，一旦检测到验证码，将全自动执行最后提交，无需手动点击助手按钮。")
            
            # 手动输入短信验证码的自动化监测逻辑
            # 目标输入框一般在特定的 div container 里
            sms_input_xpath = "//input[@placeholder='请输入短信验证码']"
            final_submit_xpath = "/html/body/div[2]/div[2]/div[2]/div[4]/div/div/footer/button"
            
            sms_detected = False
            for timeout_counter in range(120): # 最多等待 120 秒
                try:
                    # 检查输入框内容
                    code_val = target_page.eval_on_selector(sms_input_xpath, "el => el.value")
                    if code_val and len(code_val) >= 4: # 通常验证码为4-6位
                        logger(f"✅ 侦测到已填写验证码: {code_val}，准备自动提交...")
                        sms_detected = True
                        break
                except Exception:
                    pass
                
                if timeout_counter % 10 == 0 and timeout_counter > 0:
                    logger(f"等待输入验证码中 ({timeout_counter}s/120s)...")
                
                target_page.wait_for_timeout(1000)
            
            if not sms_detected:
                logger("⚠️ 等待验证码超时，请您手动点击网页上的提交按钮。")
                captcha_callback() # 托底：如果自动监测失败，还是弹个窗提醒一下
            else:
                smart_wait(1000)
                logger(f"🚀 自动执行最终提交: {final_submit_xpath}")
                try:
                    target_page.locator(f"xpath={final_submit_xpath}").click(timeout=5000)
                    logger("✅ 最终确认提交成功！")
                except Exception as e:
                    logger(f"⚠️ 自动点击最终提交失败: {e}，请手动点击网页确认。")

            smart_wait(2000)
            logger("🎉 自动补正提交脚本注射完毕！")
            
            return True

        except PlaywrightTimeoutError:
            logger("❌ 超时异常：执行自动化操作时未能找到元素。")
            if 'target_page' in locals() and target_page:
                try:
                    target_page.screenshot(path="debug_amend_timeout_error.png", full_page=True)
                except:
                    pass
            return False
        except Exception as e:
            logger(f"❌ 自动补正流程中发生未预期的核心错误: {str(e)}")
            if 'target_page' in locals() and target_page:
                try:
                    target_page.screenshot(path="debug_amend_error.png", full_page=True)
                except:
                    pass
            return False
