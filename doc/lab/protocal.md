# 实验方案

AWS:

|pipeline parallel size|data parallel size|microbatch size|
|-|-|-|
|3|4, 8|4, 8|
|4|2, 4, 8|4, 8, 16|
|5|2, 4|8, 16|
|7|2, 4|8, 16|

9个点：

|Node Number|Data Parallel Size|Pipeline Parallel Size|MicroBatch Size|cmds|
|:-:|:-:|:-:|:-:|:-:|
|8|2|4|4|263|
|10|2|5|4|265|
|12|4|3|4|133|
|14|2|7|8|141|
|16|4|4|8|71|
|20|4|5|16|41|
|24|8|3|8|37|
|28|4|7|16|45|
|32|8|4|16|23|

Local:

|pipeline parallel size|data parallel size|microbatch size|
|-|-|-|
|3|4|4|
|4|2, 4|4, 8|
|5|2|8|
|7|2|8|

5个点

|Node Number|Data Parallel Size|Pipeline Parallel Size|MicroBatch Size|cmds|
|:-:|:-:|:-:|:-:|:-:|
|8|2|4|4|263|
|10|2|5|8|265|
|12|4|3|4|133|
|14|2|7|8|141|
|16|4|4|8|71|