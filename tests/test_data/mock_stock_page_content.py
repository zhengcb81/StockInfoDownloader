"""
Mock stock page content for integration tests
"""

def get_mock_links():
    """返回模拟的股票页面链接数据"""
    return [
        {
            "text": "投资者关系活动记录表2024",
            "href": "/new/disclosure/detail?stockCode=000001&orgId=9900000062&announcementId=1201234567"
        },
        {
            "text": "机构调研活动纪要",
            "href": "/new/disclosure/detail?stockCode=000001&orgId=9900000062&announcementId=1201234568"
        },
        {
            "text": "2024年年度报告",
            "href": "/new/disclosure/detail?stockCode=000001&orgId=9900000062&announcementId=1201234569"
        },
        {
            "text": "投资者关系活动更正公告",
            "href": "/new/disclosure/detail?stockCode=000001&orgId=9900000062&announcementId=1201234570"
        }
    ]