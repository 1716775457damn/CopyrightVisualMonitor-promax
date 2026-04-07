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
            # 使用用户提供的精确定位 XPath 点击大卡片图片
            sub_xpath = "/html/body/div[2]/div[2]/div[2]/div/div/img[1]"
            logger(f"正在执行第二步点击：根据 XPath 按下【计算机软件著作权相关登记】 => {sub_xpath}")
            card = target_page.locator(f"xpath={sub_xpath}")
            card.wait_for(state="visible", timeout=10000)
            card.click(timeout=10000)
            target_page.wait_for_timeout(2000)
            
            # 3. 点击 R11 立即登记按钮 (使用用户提供的精确定位 XPath)
            r11_xpath = "/html/body/div[2]/div[2]/div[3]/div/table/tr[1]/td[1]/div/div[3]/button"
            logger(f"正在根据精准 DOM 路径点击 R11 【立即登记】按钮: {r11_xpath}")
            btn = target_page.locator(f"xpath={r11_xpath}")
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
            step1_next_btn = "/html/body/div[2]/div[2]/div[2]/div/div[1]"
            logger("点击须知协议: " + step1_next_btn)
            target_page.locator(f"xpath={step1_next_btn}").click(timeout=5000)
            target_page.wait_for_timeout(1000)

            # 2. 软件全称
            soft_name_path = "/html/body/div[2]/div[2]/div[2]/div[2]/div[1]/div/div[1]/div/input"
            logger("填写软件全称...")
            target_page.locator(f"xpath={soft_name_path}").fill(parsed_data.get('software_name', ''))

            # 3. 软件版本号
            soft_version_path = "/html/body/div[2]/div[2]/div[2]/div[2]/div[3]/div/div[1]/div/input"
            logger("填写软件版本号...")
            target_page.locator(f"xpath={soft_version_path}").fill(parsed_data.get('version', ''))
            
            # 点击下一步
            step2_next_btn = "/html/body/div[2]/div[2]/div[2]/div[4]/button[2]"
            logger("点击下一步进入第2页...")
            target_page.locator(f"xpath={step2_next_btn}").click(timeout=5000)
            target_page.wait_for_timeout(2000)

            logger("====== 开始自动填写软著登记表单 (第2页) ======")
            
            # 软件分类 -> 应用软件
            logger("选择软件分类: 应用软件")
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[1]/div/div/div[1]").click()
            target_page.wait_for_timeout(500)
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[1]/div/div/div[2]/div/div[2]/div[1]").click()
            
            # 开发完成日期
            logger("填写开发完成日期...")
            date_path = "/html/body/div[2]/div[2]/div[2]/div[4]/div/div/div/div[1]"
            finish_date = parsed_data.get('dev_finish_date', '')
            
            if finish_date and '-' in finish_date:
                parts = finish_date.split('-')
                if len(parts) == 3:
                    year_val = parts[0]
                    month_val = parts[1].lstrip('0')
                    day_val = parts[2].lstrip('0')
                    
                    try:
                        # 1. 点击输入框打开日期面板
                        target_page.locator(f"xpath={date_path}").click()
                        target_page.wait_for_timeout(1000)
                        
                        popup_base = "/html/body/div[2]/div[2]/div[2]/div[4]/div/div/div/div[3]"
                        
                        # 2. 选择年份
                        year_header_xpath = f"{popup_base}/div/div[1]/div/div[1]/div[1]"
                        logger(f"点击年份选择: {year_header_xpath}")
                        target_page.locator(f"xpath={year_header_xpath}").click(timeout=3000)
                        target_page.wait_for_timeout(1000)
                        # 点击具体的年份数字 (需模糊匹配，因为可能带‘年’字)
                        try:
                            target_page.locator(f"xpath={popup_base}").locator("div, span, td").filter(has_text=re.compile(f"^{year_val}年?$")).first.click(timeout=3000)
                        except:
                            target_page.locator(f"xpath={popup_base}").locator(f"text={year_val}").first.click(timeout=3000)
                        target_page.wait_for_timeout(800)
                        
                        # 3. 选择月份
                        month_header_xpath = f"{popup_base}/div/div[1]/div/div[2]/div[1]"
                        logger(f"点击月份选择: {month_header_xpath}")
                        target_page.locator(f"xpath={month_header_xpath}").click(timeout=3000)
                        target_page.wait_for_timeout(800)
                        # 点击具体的月份数字 (可能是 "10" 或是 "10月")
                        try:
                            target_page.locator(f"xpath={popup_base}").locator("div, span, td").filter(has_text=re.compile(f"^{month_val}月?$")).first.click(timeout=3000)
                        except:
                            target_page.locator(f"xpath={popup_base}").locator(f"text={month_val}").first.click(timeout=3000)
                        target_page.wait_for_timeout(800)
                        
                        # 4. 选择日期
                        logger(f"点击日期: {day_val}")
                        day_table_xpath = f"{popup_base}/div/div[2]/div/table"
                        # 避免点到上个月或下个月的同名日期，通常会有 class 区分（如 .available, .current 等），如果用精确文本匹配一般是安全的选择，或者简单地利用 playwright 内置的寻找可见的精确元素
                        day_cell = target_page.locator(f"xpath={day_table_xpath}").locator("td").filter(has_text=re.compile(f"^{day_val}$")).first
                        day_cell.click(timeout=3000)
                        target_page.wait_for_timeout(500)
                        
                        logger(f"✅ 开发完成日期 {finish_date} 自动化选择成功。")
                    except Exception as e:
                        logger(f"⚠️ 自动化选择日期面板失败: {e}，尝试回退到手动输入点击...")
                        target_page.locator(f"xpath={date_path}").click()
            else:
                target_page.locator(f"xpath={date_path}").click()
            
            # 点击下一步
            step3_next_btn = "/html/body/div[2]/div[2]/div[2]/div[7]/button[2]"
            logger("点击下一步进入第3页...")
            target_page.locator(f"xpath={step3_next_btn}").click(timeout=5000)
            target_page.wait_for_timeout(2000)
            
            logger("====== 开始自动填写软著登记表单 (运行环境、功能描述等) ======")
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[1]/div/div/textarea").fill(parsed_data.get('dev_hardware', '')) # 开发硬件环境
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[2]/div/div/textarea").fill(parsed_data.get('run_hardware', '')) # 运行硬件环境
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[3]/div/div/textarea").fill(parsed_data.get('dev_os', '')) # 开发操作系统
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[4]/div/div/textarea").fill(parsed_data.get('dev_tools', '')) # 开发软件环境
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[5]/div/div/textarea").fill(parsed_data.get('run_platform', '')) # 运行平台
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[6]/div/div/textarea").fill(parsed_data.get('support_software', '')) # 支撑软件
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[7]/div/div[2]/textarea").fill(parsed_data.get('language', '')) # 编程语言
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[8]/div/div/div[1]/div/input").fill(parsed_data.get('source_lines', '')) # 源程序量
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[9]/div/div/textarea").fill(parsed_data.get('dev_purpose', '')) # 开发目的
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[10]/div/div/textarea").fill(parsed_data.get('target_domain', '')) # 面向领域
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[11]/div/div/textarea").fill(parsed_data.get('main_functions', '')) # 主要功能
            target_page.locator(f"xpath=/html/body/div[2]/div[2]/div[2]/div[12]/div/div[2]/textarea").fill(parsed_data.get('tech_features', '')) # 技术特点
            
            # 下一步
            step4_next_btn = "/html/body/div[2]/div[2]/div[2]/div[16]/button[2]"
            target_page.locator(f"xpath={step4_next_btn}").scroll_into_view_if_needed()
            target_page.wait_for_timeout(500)
            logger("点击下一步进入最后阶段...")
            target_page.locator(f"xpath={step4_next_btn}").click(timeout=5000)
            
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
