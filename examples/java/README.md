# Java ActionListener 最小调度示例

该示例真实使用 `java.awt.event.ActionListener` 和 `ActionEvent`，以无窗口的命令行程序说明作业题 2.1 中的监听与调度关系。Actor 和 Reviewer 仅模拟工作，不调用大模型或网络。项目主体仍由 Python 实现。

在仓库根目录执行（JDK 11 或更高版本；本项目实际验证版本为 11.0.28）：

```sh
javac --release 11 -d outputs/java examples/java/AgentActionListenerDemo.java
java -cp outputs/java AgentActionListenerDemo
```

`outputs/` 被 Git 忽略，编译结果不会进入公共源码。

事件源通过 `listener.actionPerformed(event)` 同步调用监听器；这个接口本身不提供新线程。监听器回调仅把任务交给 `ExecutorService`，后台任务才执行 Actor 或 Reviewer。Actor 发布完成事件后才安排 Reviewer，主线程通过带超时的 `CompletableFuture.get` 等待结果，退出时关闭并等待线程池。

程序检查实际执行顺序为 `Actor -> Reviewer -> Completed`，打印主线程及工作线程名称。线程编号可能随线程池调度变化，但业务先后关系固定。

| Java 示例 | Python 主项目的对应设计 |
| --- | --- |
| `ActionEvent` 的命令与来源 | `Event` 的类型、任务标识及状态 |
| 注册 `ActionListener` | `EventBus.subscribe` 注册回调 |
| 回调向线程池投递任务 | 工作流引擎协调异步任务与工具调用 |
| Actor 完成后才发布事件 | `WorkflowEngine` 保证取证、回答、复核的阶段顺序 |
| 等待完成并关闭执行器 | 有界执行、取消处理与网关生命周期管理 |

这段示例只证明监听回调可以参与调度。依赖关系、重复事件处理、超时、重试和终止规则仍需要应用自行设计，不能由 `ActionListener` 接口推出。Python 项目的相应规则由状态机、事件总线和受控网关落实。
