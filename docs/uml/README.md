# UML design

The editable PlantUML files describe the implemented educational workflow. SVG and PNG files provide readable diagram views. All examples and labels in this directory are anonymous.

| Diagram | Scope |
| --- | --- |
| `01_use_cases` | Import, ask, evaluate, and programmatic cancellation |
| `02_components` | Application, model API, and MCP subprocess boundaries |
| `03_classes` | Core classes and the shared gateway interface |
| `04_states` | Optimized workflow; every active state supports error and cancellation |
| `05_sequence` | MCP initialization, tool discovery, invocation, and content return |
| `06_activity` | Bounded revision and evidence-governed completion |

`WorkflowEngine.cancel(task_id)` is an API; the CLI does not offer a separate interactive cancellation screen. `baseline` calls `LocalGateway` via its counting wrapper. `engineered` and `optimized` use `GuardedGateway`, normally around `MCPGateway`. The evidence gate establishes reference identity and excerpt membership, not semantic entailment. State diagrams omit repeated error edges in rendered views for readability; the editable source lists them.

Sources use class names in `src/docagent/core.py` and `src/docagent/gateway.py`. MCP initialization and tool execution use protocol `2025-06-18` with the pinned Python SDK.
