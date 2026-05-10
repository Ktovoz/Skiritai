# Auto-generated replay script
# Step: open_baidu

async def run(page, context):
    await page.goto("https://www.baidu.com")
    await page.wait_for_load_state("networkidle")