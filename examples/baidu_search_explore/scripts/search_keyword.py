# Auto-generated replay script
# Step: search_keyword

async def run(page, context):
    await page.evaluate("document.getElementById('kw').value = 'Playwright 自动化测试'; document.getElementById('su').click();")