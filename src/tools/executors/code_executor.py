# encoding: utf-8
import requests

from .base_executor import BaseExecutor
from config import CODE_RUNNER_API_URL

class CodeExecutor(BaseExecutor):

    def execute(self, code, *args, **kwargs):

        code_prefix = """import matplotlib
import matplotlib.pyplot as plt

matplotlib.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams["axes.unicode_minus"] = False
"""
        url = CODE_RUNNER_API_URL
        data = {
            'id': "1111",
            'code_text': code_prefix + "\n" + code,
        }
        response = requests.post(url, json=data).json()
        return response['data']


"""
```
        #### 1.输入示例
code_text = \"\"\"import matplotlib.pyplot as plt

print("hello world!")

# 示例数据
x = [1, 2, 3, 4, 5]
y = [2, 3, 5, 7, 11]

# 创建图形和轴
plt.figure()

# 绘制折线图
plt.plot(x, y, marker='o', linestyle='-', color='b', label='Line Plot')

# 添加标题和标签
plt.title('Simple Line Plot')
plt.xlabel('X-axis')
plt.ylabel('Y-axis')

# 添加图例
plt.legend()

# 显示图形
plt.show()

print("finish!")

\"\"\"

data = {
    "id": 1111,
    "code_text": code_text,
    "code_type":"python"
}
```

#### 2.正确输出示例
```
{
	'id': '1111', 
	'code': 200, 
	'data': [
		{'text': 'hello world!\n'}, 
		{'img': 'iVBORw0KGgoAAAANSUhEUgAAAjMAAAHFCAYAAAAHcXhbAAAAOXRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjYuMiwgaHR0cHM6Ly9tYXRwbG90bGliLm9yZy8o6BhiAAAACXBIWXMAAA9hAAAPY……(省略)ggg=='}, 
		{'text': 'finish!\n'}
		], 
    'msg': 'success', 
    'time': 0.711
}
```

#### 3.错误输出示例
```
{
	'id': '1111', 
	'code': 500, 
	'data': None, 
	'msg': 'No available kernels, please try again later.', 
	'time': 0.0
}
```

"""