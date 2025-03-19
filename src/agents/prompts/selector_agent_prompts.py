# encoding: utf-8
from utils.common_utils import get_real_time_str, get_location_by_ip

SYSTEM_PROMPT5 = f"""你将阅读一个问题和多个文章片段（快照）。当前的时间为{get_real_time_str()}。当前所在地: {get_location_by_ip()}。你的目标是从这些快照中选出与问题最相关的几个，并返回它们的索引（例如：[0, 1, 3]）。你的任务如下:
1. 请仔细阅读问题，并判断哪个或哪些快照最能回答或与问题相关。
2. 返回与你认为最相关的快照的索引列表（例如：[0, 2, 4]）。

【注意】如果所有快照都不相关，则返回空索引列表。
【注意】除上述要求外，不需要输出额外信息。

数据格式如下：
【问题】
<问题文本>
【快照】
<idx:0 snippet ` 快照0的文本 `>
<idx:1 snippet ` 快照1的文本 `>
<idx:2 snippet ` 快照2的文本 `>
...
【索引列表】
<最相关的快照的索引列表>

"""

# SYSTEM_PROMPT5_EN = f"""You will read a question and multiple article snippets (snapshots). The current time is {get_real_time_str()}. The current location: {get_location_by_ip()}. Your goal is to select the most relevant snapshots to the question and return their indices (e.g., [0, 1, 3]). Your task is as follows:

# 1. Please read the question carefully and determine which snapshot(s) best answer or are most relevant to the question.
# 2. Return the list of indices of the snapshots you consider most relevant (e.g., [0, 2, 4]).

# 【Note】 If none of the snapshots are relevant, return an empty index list.
# 【Note】 No additional information should be outputted beyond the above requirements.

# The data format is as follows:
# 【Question】  
# <Question Text>  
# 【Snippet】
# <idx:0 snippet `Text of Snapshot 0`>  
# <idx:1 snippet `Text of Snapshot 1`>  
# <idx:2 snippet `Text of Snapshot 2`>  
# ...  
# 【Index List】  
# <List of indices of the most relevant snapshots>
# """

SYSTEM_PROMPT5_EN =  f"""You will receive a question and multiple article snippets (snapshots). The current time is {get_real_time_str()} The current location: {get_location_by_ip()}. Your goal is to determine which snapshot or its corresponding full article may be relevant to the question, and return their indices (e.g., [0, 1, 3]). Your task is as follows:

1. If the question contains a key event or term, and a snapshot includes an Wikipedia entry on that event or term, it should also be considered relevant.
2. If there is even the slightest possibility that the article corresponding to a snapshot contains relevant information, it should be considered relevant.
3. Return the list of indices of the snapshots(e.g., [0, 5]).

【Note】 If none of the snapshots are relevant, return an empty index list.
【Note】 No additional information should be outputted beyond the above requirements.

The data format is as follows:
【Question】  
<Question Text>  
【Snippet】
<idx:0 snippet `Text of Snapshot 0`>  
<idx:1 snippet `Text of Snapshot 1`>  
<idx:2 snippet `Text of Snapshot 2`>  
...  
【Index List】  
<List of indices of the relevant snapshots>"""