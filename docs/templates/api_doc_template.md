# API Documentation Template

Use this template when creating API documentation for modules.

---

## Module Name

Brief description of the module's purpose and functionality.

### Overview

- **Module Path**: `src/package/module_name`
- **Purpose**: One-line description
- **Dependencies**: List of dependencies

### Classes

#### ClassName

Brief class description.

```python
from src.package.module import ClassName

instance = ClassName(param1="value", param2=123)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `param1` | str | required | Description of param1 |
| `param2` | int | `0` | Description of param2 |
| `param3` | bool | `True` | Description of param3 |

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `attr1` | str | Description of attr1 |
| `attr2` | int | Description of attr2 |

**Methods:**

##### method_name

Brief method description.

```python
result = instance.method_name(arg1, arg2="value")
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `arg1` | str | required | Description of arg1 |
| `arg2` | str | `"default"` | Description of arg2 |

**Returns:** `ReturnType` - Description of return value

**Raises:**
- `ExceptionType`: When this exception is raised

**Example:**

```python
from src.package.module import ClassName

instance = ClassName()
result = instance.method_name("test")
print(result)
```

### Functions

#### function_name

Brief function description.

```python
from src.package.module import function_name

result = function_name(param1, param2="value")
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `param1` | str | required | Description of param1 |
| `param2` | str | `"default"` | Description of param2 |

**Returns:** `ReturnType` - Description of return value

**Raises:**
- `ExceptionType`: When this exception is raised

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `CONSTANT_NAME` | `"value"` | Description of constant |

### Usage Examples

#### Basic Usage

```python
# Basic example code
from src.package.module import ClassName

instance = ClassName()
result = instance.method()
```

#### Advanced Usage

```python
# Advanced example with multiple features
from src.package.module import ClassName, function_name

# Setup
instance = ClassName(param1="value")

# Execution
result = instance.method()
processed = function_name(result)
```

### Error Handling

Describe common errors and how to handle them:

```python
from src.package.module import ClassName
from src.core.exceptions import SpecificError

try:
    instance = ClassName()
    result = instance.risky_operation()
except SpecificError as e:
    print(f"Operation failed: {e}")
```

### Performance Considerations

- Time complexity: O(n)
- Space complexity: O(1)
- Thread safety: Yes/No

### See Also

- [Related Module 1](../api/related1.md) - Description
- [Related Module 2](../api/related2.md) - Description
- [Guide](../guides/guide_name.md) - Related guide

---

## Documentation Checklist

Before submitting API documentation, verify:

- [ ] Module description is clear and concise
- [ ] All public classes are documented
- [ ] All public methods are documented
- [ ] All public functions are documented
- [ ] Parameters include type information
- [ ] Return values are documented
- [ ] Exceptions are documented
- [ ] Code examples are tested and working
- [ ] Cross-references are correct
- [ ] Formatting is consistent
