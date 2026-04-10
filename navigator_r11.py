import logging
import re
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

def execute_r11_registration(parsed_data: dict, code_pdf_path: str, doc_pdf_path: str, logger=print) -> bool:
    """
    Connects to an existing Edge browser on port 9222 and performs
    precise navigation and clicking for the R11 software registration using pure JS.
    """
    with sync_playwright() as p:
        try:
            logger("正在通过 CDP (端口9222) 连接至 Edge 浏览器...")
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            
            context = browser.contexts[0]
            target_page = None
            
            # 清理多余标签页，确保只留下一个操作主窗口，防止发生 Target closed 错误
            for page in context.pages:
                if "register.ccopyright" in page.url or "register.html" in page.url or "account.html" in page.url:
                    if target_page is None:
                        target_page = page
                    else:
                        try:
                            # 已经选定了一个目标页了，把其他的重复标签关掉
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
            logger("✅ 成功接管版权官网页面，开始底层 JS 自动化导航操作...")

            # 1. 导航到“版权登记”并点击
            logger("正在执行第一步点击：【版权登记】菜单...")
            target_page.locator("text=版权登记").click(timeout=10000)
            target_page.wait_for_timeout(1500)
            
            # 2. 点击“计算机软件著作权相关登记”
            logger("正在执行第二步点击：寻找【计算机软件著作权相关登记】入口...")
            # 宽泛匹配，寻找包含文字的容器或图片
            card = target_page.locator("xpath=//div[contains(text(), '计算机软件著作权')] | //img[contains(@src, 'soft')]").first
            card.wait_for(state="visible", timeout=10000)
            card.click(timeout=10000)
            target_page.wait_for_timeout(2000)
            
            # 3. 点击 R11 立即登记按钮 
            logger("正在寻找 R11 【立即登记】按钮...")
            # 寻找 R11 标题后最近的立即登记按钮，或者页面上的第一个立即登记按钮
            btn = target_page.locator("xpath=(//div[contains(text(), 'R11') or contains(text(), 'r11')]/following::button[contains(text(), '立即')])[1] | (//button[contains(text(), '立即登记')])[1]").first
            btn.wait_for(state="visible", timeout=15000)
            # 为了防止被 header 等浮动元素遮挡，强行进行底部物理暴露后点击
            btn.scroll_into_view_if_needed()
            target_page.wait_for_timeout(500)
            btn.click(timeout=5000)
            
            logger("✅ 已成功击中 R11 【立即登记】按钮！")
            target_page.wait_for_timeout(3000)
            
            # --- 以下进入软著信息填写流程表单阶段 ---
            logger("====== 开始自动填写软著登记表单 (第1页) ======")
            
            # 1. 须知页/或前置页 点击下一步
            logger("点击须知协议: 寻找【下一步】或同意声明...")
            target_page.locator("xpath=//div[contains(@class,'checkbox')] | //span[contains(text(), '我已阅读')] | //input[@type='checkbox']").first.click(timeout=5000)
            target_page.wait_for_timeout(1000)

            # 2. 软件全称
            logger("填写软件全称...")
            target_page.locator("xpath=(//div[contains(text(), '软件全称')]/following::input)[1] | //input[@placeholder='请输入软件全称']").first.fill(parsed_data.get('software_name', ''))

            # 3. 软件版本号
            logger("填写软件版本号...")
            target_page.locator("xpath=(//div[contains(text(), '版本号')]/following::input)[1] | //input[@placeholder='例如：V1.0']").first.fill(parsed_data.get('version', ''))
            
            # 点击下一步
            logger("点击下一步进入第2页...")
            # 寻找页面底部的最后一个 button 或文字包含下一步的 button
            target_page.locator("xpath=(//button[contains(text(), '下一步')])[1] | //div[contains(@class, 'footer')]//button[not(contains(text(), '返回'))]").first.click(timeout=5000)
            target_page.wait_for_timeout(2000)

            logger("====== 开始自动填写软著登记表单 (第2页) ======")
            
            # 软件分类 -> 应用软件
            logger("选择软件分类: 应用软件")
            target_page.locator("xpath=(//div[contains(text(), '软件分类')]/following::input)[1] | //input[@placeholder='请选择软件分类']").first.click(timeout=5000)
            target_page.wait_for_timeout(500)
            target_page.get_by_text("应用软件", exact=True).first.click(timeout=5000)
            
            # 开发完成日期 (使用底层 JS 强制注入，绕过极度脆弱的日历面板组件操作)
            logger("填写开发完成日期 (使用底层 JS 注入方式)...")
            finish_date = parsed_data.get('dev_finish_date', '')
            if finish_date:
                try:
                    date_input = target_page.locator("xpath=(//div[contains(text(), '开发完成日期')]/following::input)[1] | //input[contains(@placeholder, '日期')]").first
                    # 使用 Playwright 的 evaluate 在浏览器内部执行 JS，强行给表单赋值并派发事件触发前端框架(如Vue/React)的双向绑定更新
                    js_code = f"""(el) => {{
                        el.value = '{finish_date}';
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        // 若挂载了特殊的 DatePicker 对象，尝试触发 blur
                        el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    }}"""
                    date_input.evaluate(js_code)
                    logger(f"✅ 开发完成日期 {finish_date} 底层强注成功，彻底避免了由于月份变化造成的日历死锁。")
                    target_page.wait_for_timeout(500)
                except Exception as e:
                    logger(f"⚠️ 日期注入遭遇异常，回退尝试暴力覆盖: {e}")
                    try:
                        date_input.fill(finish_date, force=True)
                    except:
                        pass
            
            # 点击下一步
            step3_next_btn = "/html/body/div[2]/div[2]/div[2]/div[7]/button[2]"
            logger("点击下一步进入第3页...")
            target_page.locator(f"xpath={step3_next_btn}").click(timeout=5000)
            target_page.wait_for_timeout(2000)
            
            logger("====== 开始自动填写软著登记表单 (运行环境、功能描述等) ======")
            
            def fill_textarea(label_text, value):
                if value:
                    target_page.locator(f"xpath=(//div[contains(text(), '{label_text}')]/following::textarea)[1] | //textarea[contains(@placeholder, '{label_text}')]").first.fill(value)
                    
            def fill_input(label_text, value):
                if value:
                    target_page.locator(f"xpath=(//div[contains(text(), '{label_text}')]/following::input)[1] | //input[contains(@placeholder, '{label_text}')]").first.fill(value)

            fill_textarea('开发硬件环境', parsed_data.get('dev_hardware', ''))
            fill_textarea('运行硬件环境', parsed_data.get('run_hardware', ''))
            fill_textarea('开发该软件的操作系统', parsed_data.get('dev_os', ''))
            fill_textarea('软件开发环境', parsed_data.get('dev_tools', ''))
            fill_textarea('运行平台', parsed_data.get('run_platform', ''))
            fill_textarea('软件运行支撑环境', parsed_data.get('support_software', ''))
            fill_textarea('编程语言', parsed_data.get('language', ''))
            fill_input('源程序量', parsed_data.get('source_lines', ''))
            fill_textarea('开发目的', parsed_data.get('dev_purpose', ''))
            fill_textarea('面向领域', parsed_data.get('target_domain', ''))
            fill_textarea('软件的主要功能', parsed_data.get('main_functions', ''))
            fill_textarea('软件的技术特点', parsed_data.get('tech_features', ''))
            
            # 下一步
            logger("点击下一步进入最后阶段...")
            step4_next_btn = target_page.locator("xpath=(//button[contains(text(), '下一步')])[1] | //div[contains(@class, 'footer')]//button[not(contains(text(), '返回'))]").last
            step4_next_btn.scroll_into_view_if_needed()
            target_page.wait_for_timeout(500)
            step4_next_btn.click(timeout=5000)
            
            logger("✅ 自动化输入流程脚本注射完毕。")

            logger("✅ 基础表单输入完毕！现在请手动检查并上传材料。")

            # --- 附件上传交互转移至人工 ---
            logger("====== 等待人工上传鉴别材料并点击“下一步”... ======")
            
            # 循环等待直到出现“保存并提交申请”按钮（意味着用户已经点击了下一步）
            submit_btn_xpath = "/html/body/div[2]/div[2]/div[2]/div[4]/button[3]"
            
            while True:
                try:
                    submit_btn = target_page.locator(f"xpath={submit_btn_xpath}")
                    # 使用较短的超时时间轮询
                    submit_btn.wait_for(state="visible", timeout=2000)
                    logger("✅ 侦测到已进入最后提交流程页！开始自动提交...")
                    break
                except Exception:
                    # 按钮未出现，说明用户还在上传页面，继续等待
                    pass
                target_page.wait_for_timeout(1000) # 休眠1秒再查

            # ==== 自动提交与打印签章页流程 ====
            try:
                # 1. 保存并提交申请
                logger("点击：保存并提交申请...")
                try:
                    target_page.locator(f"xpath={submit_btn_xpath}").click(timeout=5000)
                except Exception as e:
                    logger(f"⚠️ [智能降级] '保存并提交申请'绝对定位失效，尝试文本匹配: {e}")
                    btn = target_page.locator("button, span.el-button").filter(has_text=re.compile(r"保存并提交申请")).first
                    if btn.count() > 0:
                        btn.click(timeout=5000)
                    else:
                        raise e
                    
                target_page.wait_for_timeout(3000)
                
                # 2. 打印签章页
                print_seal_xpath = "/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/button[1]"
                logger("点击：打印签章页...")
                # 有些系统点击打印会弹出一个新标签页，这里做拦截处理
                pages_before = len(target_page.context.pages)
                
                try:
                    target_page.locator(f"xpath={print_seal_xpath}").click(timeout=10000)
                except Exception as e:
                    logger(f"⚠️ [智能降级] '打印签章页'绝对定位失效，尝试文本匹配: {e}")
                    btn = target_page.locator("button, span.el-button").filter(has_text=re.compile(r"打印签章页")).first
                    if btn.count() > 0:
                        btn.click(timeout=5000)
                    else:
                        raise e
                        
                target_page.wait_for_timeout(3000)
                
                # 检查是否弹出了新页面
                operate_page = target_page
                if len(target_page.context.pages) > pages_before:
                    logger("✅ 检测到弹出了新标签页，切换至新页面操作打印。")
                    operate_page = target_page.context.pages[-1]
                    operate_page.wait_for_load_state()
                
                # 3. 打印界面 - 打印
                print_act1_xpath = "/html/body/div[2]/div[2]/div/div/div[1]/button"
                logger("点击：打印（界面确认）...")
                try:
                    operate_page.locator(f"xpath={print_act1_xpath}").click(timeout=10000)
                except Exception as e:
                    logger(f"⚠️ 通过绝对路径点击第一次打印失败，切换智能文本匹配: {e}")
                    # 寻找包含“打印”文本的按钮并点击
                    btn = operate_page.locator("button, span.el-button, div[role='button']").filter(has_text=re.compile(r"打印")).first
                    if btn.count() > 0:
                        btn.click(timeout=5000)
                        logger("✅ 智能文本匹配 打印 按钮成功！")
                    else:
                        raise e
                
                operate_page.wait_for_timeout(2000)
                
                # 4. 打印界面 - 二次打印确认
                print_act2_xpath = "/html/body/div[2]/div[2]/div/div/div[1]/button[2]"
                logger("点击：二次确认打印...")
                try:
                    operate_page.locator(f"xpath={print_act2_xpath}").click(timeout=10000)
                except Exception as e:
                    logger(f"⚠️ 通过绝对路径点击第二次打印失败，切换智能文本匹配: {e}")
                    # 寻找包含“打印”或者“确认”/“确定”文本的按钮
                    btn = operate_page.locator("button, span.el-button, div[role='button']").filter(has_text=re.compile(r"打印|确认|确定")).last
                    if btn.count() > 0:
                        btn.click(timeout=5000)
                        logger("✅ 智能文本匹配 二次确认 按钮成功！")
                    else:
                        raise e
                
                operate_page.wait_for_timeout(2000)
                
                logger("🎉 所有提交与签章页唤起流程执行完毕！")

            except Exception as e:
                logger(f"⚠️ 自动提交流程中途受阻，请手动完成最后几步: {e}")

            return True

        except PlaywrightTimeoutError:
            logger("❌ 超时异常：连接浏览器或执行操作失败。")
            if 'target_page' in locals() and target_page:
                target_page.screenshot(path="debug_r11_timeout_error.png", full_page=True)
            return False
        except Exception as e:
            logger(f"❌ 导航过程中发生未预期的错误: {str(e)}")
            if 'target_page' in locals() and target_page:
                target_page.screenshot(path="debug_r11_unexpected_error.png", full_page=True)
            return False
