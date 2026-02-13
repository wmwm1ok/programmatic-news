"""
邮件发送模块
支持发送 HTML 正文邮件
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import List


class EmailSender:
    """邮件发送器"""
    
    def __init__(self, smtp_server: str = None, smtp_port: int = None,
                 username: str = None, password: str = None,
                 from_addr: str = None, to_addr: str = None):
        """
        初始化邮件发送器
        参数优先使用传入值，否则从环境变量读取
        """
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.username = username or os.getenv('EMAIL_USERNAME')
        self.password = password or os.getenv('EMAIL_PASSWORD')
        self.from_addr = from_addr or os.getenv('EMAIL_FROM') or self.username
        self.to_addr = to_addr or os.getenv('EMAIL_TO', 'wangmeng42@baidu.com')
        
    def send_html_email(self, subject: str, html_content: str, to_addrs: List[str] = None) -> bool:
        """
        发送 HTML 邮件（正文形式）
        
        Args:
            subject: 邮件主题
            html_content: HTML 正文内容
            to_addrs: 收件人列表，默认使用初始化时设置的 to_addr
            
        Returns:
            bool: 发送是否成功
        """
        if not self.username or not self.password:
            print("❌ 错误: 未设置邮箱用户名或密码")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = self.from_addr
            
            # 设置收件人
            recipients = to_addrs or [self.to_addr]
            msg['To'] = ', '.join(recipients)
            
            # 添加 HTML 内容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 连接 SMTP 服务器并发送
            print(f"📧 正在连接 SMTP 服务器: {self.smtp_server}:{self.smtp_port}")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # 启用 TLS 加密
                print(f"🔐 正在登录: {self.username}")
                server.login(self.username, self.password)
                
                print(f"📤 正在发送邮件到: {', '.join(recipients)}")
                server.sendmail(self.from_addr, recipients, msg.as_string())
                
            print("✅ 邮件发送成功")
            return True
            
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            import traceback
            traceback.print_exc()
            return False


def send_weekly_report(html_content: str, start_date: str, end_date: str) -> bool:
    """
    发送周报邮件
    
    Args:
        html_content: HTML 报告内容
        start_date: 报告开始日期
        end_date: 报告结束日期
        
    Returns:
        bool: 发送是否成功
    """
    sender = EmailSender()
    subject = f"竞品周报 {start_date} ~ {end_date}"
    
    return sender.send_html_email(subject, html_content)
