# 助手系统API文档

## 1. 通用信息

### 1.1 基础URL

所有API请求的基础URL为：`/api/`

### 1.2 认证

所有API请求需要在请求头中包含认证信息。

### 1.3 通用响应格式

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

## 2. 助手管理 (Assistant)

### 2.1 获取助手列表

**请求**

- 方法: `GET`
- 路径: `/assistants/`
- 描述: 返回所有可用的助手，默认只返回激活状态的助手

**查询参数**

- `is_active`: 布尔值，是否只返回激活的助手
- `is_memory`: 布尔值，根据是否启动记忆过滤
- `search`: 字符串，搜索助手名称或描述
- `ordering`: 字符串，排序字段，可选值：name, created_at, updated_at

**响应示例**

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "results": [
      {
        "id": 1,
        "name": "助手名称",
        "description": "助手描述",
        "is_active": true,
        "is_memory": true,
        "prompt_template": "提示词模板",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z"
      }
    ]
  }
}
```

### 2.2 获取助手详情

**请求**

- 方法: `GET`
- 路径: `/assistants/{id}/`
- 描述: 根据ID获取特定助手的详细信息

**响应示例**

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": 1,
    "name": "助手名称",
    "description": "助手描述",
    "is_active": true,
    "is_memory": true,
    "prompt_template": "提示词模板",
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
}
```

## 3. 助手模板管理 (AssistantTemplates)

### 3.1 获取助手模板列表

**请求**

- 方法: `GET`
- 路径: `/assistant-templates/`
- 描述: 返回所有可用的助手模板

**查询参数**

- `is_default`: 布尔值，根据是否为默认模板过滤
- `search`: 字符串，搜索模板名称或提示词
- `ordering`: 字符串，排序字段，可选值：name, created_at, updated_at

**响应示例**

```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "id": 1,
      "name": "模板名称",
      "prompt_template": "提示词模板",
      "is_default": false,
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2023-01-01T00:00:00Z"
    }
  ]
}
```

### 3.2 获取助手模板详情

**请求**

- 方法: `GET`
- 路径: `/assistant-templates/{id}/`
- 描述: 根据ID获取特定助手模板的详细信息

**响应示例**

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": 1,
    "name": "模板名称",
    "prompt_template": "提示词模板",
    "is_default": false,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
}
```

## 4. 助手配置管理 (AssistantsConfigs)

### 4.1 获取助手配置列表

**请求**

- 方法: `GET`
- 路径: `/assistants-configs/`
- 描述: 返回用户可用的助手配置（个人配置和公共配置）

**查询参数**

- `user_id`: 整数，根据用户ID过滤
- `name`: 字符串，根据配置名称过滤
- `is_public`: 布尔值，是否为公共配置
- `search`: 字符串，搜索配置名称、关系、昵称或性格
- `ordering`: 字符串，排序字段，可选值：name, id

**响应示例**

```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "id": 1,
      "user_id": 1,
      "name": "配置名称",
      "relationship": "朋友",
      "nickname": "用户",
      "personality": "友好",
      "greeting": "你好！",
      "dialogue_style": "轻松",
      "is_public": false
    }
  ]
}
```

### 4.2 创建助手配置

**请求**

- 方法: `POST`
- 路径: `/assistants-configs/`
- 描述: 创建新的助手配置

**请求体**

```json
{
  "user_id": 1,
  "name": "配置名称",
  "relationship": "朋友",
  "nickname": "用户",
  "personality": "友好",
  "greeting": "你好！",
  "dialogue_style": "轻松",
  "is_public": false
}
```

**响应示例**

```json
{
  "code": 201,
  "msg": "success",
  "data": {
    "id": 1,
    "user_id": 1,
    "name": "配置名称",
    "relationship": "朋友",
    "nickname": "用户",
    "personality": "友好",
    "greeting": "你好！",
    "dialogue_style": "轻松",
    "is_public": false
  }
}
```

### 4.3 获取助手配置详情

**请求**

- 方法: `GET`
- 路径: `/assistants-configs/{id}/`
- 描述: 根据ID获取特定助手配置的详细信息

**响应示例**

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": 1,
    "user_id": 1,
    "name": "配置名称",
    "relationship": "朋友",
    "nickname": "用户",
    "personality": "友好",
    "greeting": "你好！",
    "dialogue_style": "轻松",
    "is_public": false
  }
}
```

### 4.4 更新助手配置

**请求**

- 方法: `PUT` 或 `PATCH`
- 路径: `/assistants-configs/{id}/`
- 描述: 更新指定的助手配置

**请求体**

```json
{
  "name": "新配置名称",
  "relationship": "导师",
  "personality": "严肃"
}
```

**响应示例**

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": 1,
    "user_id": 1,
    "name": "新配置名称",
    "relationship": "导师",
    "nickname": "用户",
    "personality": "严肃",
    "greeting": "你好！",
    "dialogue_style": "轻松",
    "is_public": false
  }
}
```

### 4.5 删除助手配置

**请求**

- 方法: `DELETE`
- 路径: `/assistants-configs/{id}/`
- 描述: 删除指定的助手配置

**响应示例**

```json
{
  "code": 204,
  "msg": "删除成功",
  "data": null
}
```

## 5. 用户助手模板管理 (UsersAssistantTemplates)

### 5.1 获取用户助手模板列表

**请求**

- 方法: `GET`
- 路径: `/users-assistant-templates/`
- 描述: 获取当前用户的助手模板，如果不存在则返回空列表

**查询参数**

- `user_id`: 整数，根据用户ID过滤
- `search`: 字符串，搜索模板名称
- `ordering`: 字符串，排序字段，可选值：name, created_at, updated_at

**响应示例**

```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "id": 1,
      "user_id": 1,
      "name": "模板名称",
      "prompt_template": "提示词",
      "is_premium_template": false,
      "is_default": true,
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2023-01-01T00:00:00Z"
    }
  ]
}
```

### 5.2 获取用户助手模板详情

**请求**

- 方法: `GET`
- 路径: `/users-assistant-templates/{id}/`
- 描述: 根据ID获取特定用户助手模板的详细信息

**响应示例**

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": 1,
    "user_id": 1,
    "name": "模板名称",
    "prompt_template": "提示词",
    "is_premium_template": false,
    "is_default": true,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
}
```

### 5.3 更新用户助手模板

**请求**

- 方法: `PUT` 或 `PATCH`
- 路径: `/users-assistant-templates/{id}/`
- 描述: 更新指定的用户助手模板

**请求体**

```json
{
  "name": "新模板名称",
  "prompt_template": "新提示词",
  "is_default": true
}
```

**响应示例**

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": 1,
    "user_id": 1,
    "name": "新模板名称",
    "prompt_template": "新提示词",
    "is_premium_template": false,
    "is_default": true,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
}
```

### 5.4 生成用户助手模板

**请求**

- 方法: `POST`
- 路径: `/users-assistant-templates/generate/`
- 描述: 从助手模板和助手配置生成用户助手模板

**请求体**

```json
{
  "template_id": 1,
  "config_id": 1,
  "name": "生成的模板",
  "is_default": false
}
```

**响应示例**

```json
{
  "code": 201,
  "msg": "success",
  "data": {
    "id": 1,
    "user_id": 1,
    "name": "生成的模板",
    "prompt_template": "生成的提示词",
    "is_premium_template": false,
    "is_default": false,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
}
```

### 5.5 创建默认模板

**请求**

- 方法: `POST`
- 路径: `/users-assistant-templates/create_default_template/`
- 描述: 为新用户创建默认的助手模板

**响应示例**

```json
{
  "code": 201,
  "msg": "成功创建默认模板",
  "data": {
    "id": 1,
    "user_id": 1,
    "name": "默认模板",
    "prompt_template": "默认提示词",
    "is_premium_template": false,
    "is_default": true,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
}
```

## 6. 选项管理 (Options)

### 6.1 获取配置选项

**请求**

- 方法: `GET`
- 路径: `/options/available_options/`
- 描述: 获取关系、昵称和性格的可用选项，标识哪些是付费选项

**响应示例**

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "relationship": [
      {
        "value": "朋友",
        "is_premium": false
      },
      {
        "value": "导师",
        "is_premium": true
      },
      {
        "value": "Customization",
        "is_premium": true
      }
    ],
    "nickname": [
      {
        "value": "用户",
        "is_premium": false
      },
      {
        "value": "大师",
        "is_premium": true
      },
      {
        "value": "Customization",
        "is_premium": true
      }
    ],
    "personality": [
      {
        "value": "友好",
        "is_premium": false
      },
      {
        "value": "专业",
        "is_premium": true
      },
      {
        "value": "Customization",
        "is_premium": true
      }
    ],
    "user_is_premium": false
  }
}
```