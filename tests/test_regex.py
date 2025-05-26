import re
REGEX = re.compile(r'"playAddr(?:NoWaterMark)?":"([^"]+)"')
def test_regex_extract():
    sample = '{"playAddrNoWaterMark":"https://example.com/video.mp4"}'
    assert REGEX.search(sample).group(1).endswith(".mp4")
