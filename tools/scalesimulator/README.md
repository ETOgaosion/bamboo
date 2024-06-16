# simulator



你需要提供一个`json`文件，该文件描述了layer的传输关系。



`world_size`: 传输时需要的节点个数。比如说例子中是从8节点 -> 7节点。但是实际上只有5个节点需要进行layer的传输，因此world_size是5。



`layers`是一个数组，数据的每个元素是一个layer

- `sizes`: layer中每个算子的大小
- `names`: 每个算子的名字(可以瞎写)
- `ranks`:这个layer会被`ranks[0]`广播给其他的ranks

