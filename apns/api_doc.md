# APNS 服务 API 文档

## 目录

- [设备管理 API](#设备管理-api)
- [通知设置 API](#通知设置-api)
- [通知发送 API](#通知发送-api)
- [苹果内购 API](#苹果内购-api)

## 设备管理 API

### 设备令牌管理

#### 获取设备令牌列表

获取当前用户的所有设备令牌。

- **URL**: `/api/devices/tokens/`
- **方法**: `GET`
- **权限**: 需要认证
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "成功",
    "data": [
      {
        "id": 1,
        "user_id": "user123",
        "device_id": "device123",
        "device_token": "token123",
        "is_active": true,
        "created_at": 1646041200,
        "updated_at": 1646041200
      }
    ]
  }
  ```

#### 创建设备令牌

为当前用户创建新的设备令牌。

- **URL**: `/api/devices/tokens/`
- **方法**: `POST`
- **权限**: 需要认证
- **请求体**:
  ```json
  {
    "device_id": "device123",
    "device_token": "token123"
  }
  ```
- **响应**:
  ```json
  {
    "code": 201,
    "msg": "创建成功",
    "data": {
      "id": 1,
      "user_id": "user123",
      "device_id": "device123",
      "device_token": "token123",
      "is_active": true,
      "created_at": 1646041200,
      "updated_at": 1646041200
    }
  }
  ```

#### 更新设备令牌

更新指定的设备令牌。

- **URL**: `/api/devices/tokens/{id}/`
- **方法**: `PUT`
- **权限**: 需要认证
- **请求体**:
  ```json
  {
    "device_token": "new_token123",
    "is_active": true
  }
  ```
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "更新成功",
    "data": {
      "id": 1,
      "user_id": "user123",
      "device_id": "device123",
      "device_token": "new_token123",
      "is_active": true,
      "created_at": 1646041200,
      "updated_at": 1646041300
    }
  }
  ```

#### 部分更新设备令牌

部分更新指定的设备令牌。

- **URL**: `/api/devices/tokens/{id}/`
- **方法**: `PATCH`
- **权限**: 需要认证
- **请求体**:
  ```json
  {
    "is_active": false
  }
  ```
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "更新成功",
    "data": {
      "id": 1,
      "user_id": "user123",
      "device_id": "device123",
      "device_token": "token123",
      "is_active": false,
      "created_at": 1646041200,
      "updated_at": 1646041400
    }
  }
  ```

#### 删除设备令牌

删除指定的设备令牌。

- **URL**: `/api/devices/tokens/{id}/`
- **方法**: `DELETE`
- **权限**: 需要认证
- **响应**:
  ```json
  {
    "code": 204,
    "msg": "删除成功",
    "data": {}
  }
  ```

#### 激活设备令牌

激活指定的设备令牌。

- **URL**: `/api/devices/tokens/{id}/activate/`
- **方法**: `POST`
- **权限**: 需要认证
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "激活成功",
    "data": {
      "id": 1,
      "user_id": "user123",
      "device_id": "device123",
      "device_token": "token123",
      "is_active": true,
      "created_at": 1646041200,
      "updated_at": 1646041500
    }
  }
  ```

#### 停用设备令牌

停用指定的设备令牌。

- **URL**: `/api/devices/tokens/{id}/deactivate/`
- **方法**: `POST`
- **权限**: 需要认证
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "停用成功",
    "data": {
      "id": 1,
      "user_id": "user123",
      "device_id": "device123",
      "device_token": "token123",
      "is_active": false,
      "created_at": 1646041200,
      "updated_at": 1646041600
    }
  }
  ```

## 通知设置 API

### 通知设置管理

#### 获取通知设置列表

获取当前用户的所有通知设置。

- **URL**: `/api/notifications/settings/`
- **方法**: `GET`
- **权限**: 需要认证
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "成功",
    "data": [
      {
        "id": 1,
        "user_id": "user123",
        "timezone": "Asia/Shanghai",
        "notify_time": "08:00",
        "days_remaining": 21,
        "is_active": true,
        "last_sent": 1646041200,
        "created_at": 1646041200,
        "updated_at": 1646041200
      }
    ]
  }
  ```

#### 获取通知设置详情

获取指定的通知设置详情。

- **URL**: `/api/notifications/settings/{id}/`
- **方法**: `GET`
- **权限**: 需要认证
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "成功",
    "data": {
      "id": 1,
      "user_id": "user123",
      "timezone": "Asia/Shanghai",
      "notify_time": "08:00",
      "days_remaining": 21,
      "is_active": true,
      "last_sent": 1646041200,
      "created_at": 1646041200,
      "updated_at": 1646041200
    }
  }
  ```

#### 创建通知设置

创建新的通知设置，并将用户的其他通知设置设为非激活状态。

- **URL**: `/api/notifications/settings/`
- **方法**: `POST`
- **权限**: 需要认证
    - **请求体**:
      ```json
      {
        "user_id": 2,
        "notify_time": "18:15"
      }
      ```
- **响应**:
  ```json
  {
    "code": 201,
    "msg": "创建成功",
    "data": {
      "id": 1,
      "user_id": "user123",
      "timezone": "Asia/Shanghai",
      "notify_time": "08:00",
      "days_remaining": 21,
      "is_active": true,
      "last_sent": null,
      "created_at": 1646041200,
      "updated_at": 1646041200
    }
  }
  ```

#### 更新通知设置

更新指定的通知设置。

- **URL**: `/api/notifications/settings/{id}/`
- **方法**: `PUT`
- **权限**: 需要认证
- **请求体**:
  ```json
  {
    "timezone": "America/New_York",
    "notify_time": "09:00",
    "days_remaining": 20,
    "is_active": true
  }
  ```
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "更新成功",
    "data": {
      "id": 1,
      "user_id": "user123",
      "timezone": "America/New_York",
      "notify_time": "09:00",
      "days_remaining": 20,
      "is_active": true,
      "last_sent": 1646041200,
      "created_at": 1646041200,
      "updated_at": 1646041300
    }
  }
  ```

#### 部分更新通知设置

部分更新指定的通知设置。

- **URL**: `/api/notifications/settings/{id}/`
- **方法**: `PATCH`
- **权限**: 需要认证
- **请求体**:
  ```json
  {
    "notify_time": "10:00"
  }
  ```
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "更新成功",
    "data": {
      "id": 1,
      "user_id": "user123",
      "timezone": "Asia/Shanghai",
      "notify_time": "10:00",
      "days_remaining": 21,
      "is_active": true,
      "last_sent": 1646041200,
      "created_at": 1646041200,
      "updated_at": 1646041400
    }
  }
  ```

#### 获取当前激活的通知设置

获取当前用户的激活通知设置。

- **URL**: `/api/notifications/settings/active/`
- **方法**: `GET`
- **权限**: 需要认证
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "成功",
    "data": {
      "id": 1,
      "user_id": "user123",
      "timezone": "Asia/Shanghai",
      "notify_time": "08:00",
      "days_remaining": 21,
      "is_active": true,
      "last_sent": 1646041200,
      "created_at": 1646041200,
      "updated_at": 1646041200
    }
  }
  ```

#### 激活通知设置

激活指定的通知设置，并将用户的其他通知设置设为非激活状态。

- **URL**: `/api/notifications/settings/{id}/activate/`
- **方法**: `POST`
- **权限**: 需要认证
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "激活成功",
    "data": {
      "id": 1,
      "user_id": "user123",
      "timezone": "Asia/Shanghai",
      "notify_time": "08:00",
      "days_remaining": 21,
      "is_active": true,
      "last_sent": 1646041200,
      "created_at": 1646041200,
      "updated_at": 1646041500
    }
  }
  ```

#### 停用通知设置

停用指定的通知设置。

- **URL**: `/api/notifications/settings/{id}/deactivate/`
- **方法**: `POST`
- **权限**: 需要认证
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "停用成功",
    "data": {
      "id": 1,
      "user_id": "user123",
      "timezone": "Asia/Shanghai",
      "notify_time": "08:00",
      "days_remaining": 21,
      "is_active": false,
      "last_sent": 1646041200,
      "created_at": 1646041200,
      "updated_at": 1646041600
    }
  }
  ```

#### 减少剩余天数

减少当前用户激活通知设置的剩余天数。

- **URL**: `/api/notifications/settings/decrease_days/`
- **方法**: `POST`
- **权限**: 需要认证
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "更新成功",
    "data": {
      "id": 1,
      "user_id": "user123",
      "timezone": "Asia/Shanghai",
      "notify_time": "08:00",
      "days_remaining": 20,
      "is_active": true,
      "last_sent": 1646041200,
      "created_at": 1646041200,
      "updated_at": 1646041700
    }
  }
  ```

## 通知发送 API

### 发送通知

#### 发送推送通知

向指定设备发送推送通知。

- **URL**: `/api/notifications/send/`
- **方法**: `POST`
- **权限**: 需要认证
- **请求体**:
  ```json
  {
    "device_id": "device123",
    "title": "通知标题",
    "body": "通知内容",
    "app_id": "pocket_ai"
  }
  ```
- **响应**:
  ```json
  {
    "code": 201,
    "msg": "发送成功",
    "data": "发送成功"
  }
  ```

## 苹果内购 API

### 购买验证

#### 验证购买收据

验证苹果内购收据并处理购买。

- **URL**: `/purchase/verify/`
- **方法**: `POST`
- **权限**: 需要认证
- **请求体**:
  ```json
  {
    "receipt_data": "苹果收据数据",
    "user_id": 123,
    "product_id": "Monthly_Subscription",
    "transaction_id": "1000000123456789",
    "app_id": "com.example.app",
    "original_transaction_id": "1000000123456789"
  }
  ```
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "success",
    "data": {
      "id": 1,
      "user_id": 123,
      "app_id": "com.example.app",
      "product_id": "Monthly_Subscription",
      "transaction_id": "1000000123456789",
      "original_transaction_id": "1000000123456789",
      "purchase_date": "2023-01-01T12:00:00Z",
      "expires_at": "2023-02-01T12:00:00Z",
      "is_active": true,
      "is_successful": true,
      "status": "success",
      "days_remaining": 30,
      "status_display": "Success",
      "created_at": 1672574400,
      "updated_at": 1672574400
    }
  }
  ```

### 苹果服务器通知

#### 接收苹果服务器通知

接收并处理来自苹果服务器的通知（如订阅续费、取消等）。

- **URL**: `/purchase/webhook/`
- **方法**: `POST`
- **权限**: 无需认证（苹果服务器调用）
- **请求体**:
  ```json
  {
    "notification_type": "DID_RENEW",
    "app_id": "com.example.app",
    "latest_receipt": "苹果收据数据",
    "latest_receipt_info": {
      "transaction_id": "1000000123456789",
      "original_transaction_id": "1000000123456789",
      "product_id": "Monthly_Subscription",
      "purchase_date_ms": "1672574400000",
      "expires_date_ms": "1675252800000"
    },
    "auto_renew_status": true,
    "user_id": 123
  }
  ```
- **响应**:
  ```json
  {
    "status": "success"
  }
  ```

### 购买记录查询

#### 获取购买记录列表

获取用户的购买记录列表。

- **URL**: `/purchase/list/`
- **方法**: `GET`
- **权限**: 需要认证
- **查询参数**:
  - `user_id`: 用户ID
  - `is_active`: 是否活跃（true/false）
  - `app_id`: 应用ID
  - `product_id`: 产品ID
- **响应**:
  ```json
  {
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": 1,
        "user_id": 123,
        "app_id": "com.example.app",
        "product_id": "Monthly_Subscription",
        "transaction_id": "1000000123456789",
        "original_transaction_id": "1000000123456789",
        "purchase_date": "2023-01-01T12:00:00Z",
        "expires_at": "2023-02-01T12:00:00Z",
        "is_active": true,
        "is_successful": true,
        "status": "success",
        "days_remaining": 30,
        "status_display": "Success",
        "created_at": 1672574400,
        "updated_at": 1672574400
      }
    ]
  }
  ```

#### 获取单个购买记录

获取指定ID的购买记录详情。

- **URL**: `/purchase/list/{id}/`
- **方法**: `GET`
- **权限**: 需要认证
- **响应**:
  ```json
  {
    "id": 1,
    "user_id": 123,
    "app_id": "com.example.app",
    "product_id": "Monthly_Subscription",
    "transaction_id": "1000000123456789",
    "original_transaction_id": "1000000123456789",
    "purchase_date": "2023-01-01T12:00:00Z",
    "expires_at": "2023-02-01T12:00:00Z",
    "is_active": true,
    "is_successful": true,
    "status": "success",
    "days_remaining": 30,
    "status_display": "Success",
    "created_at": 1672574400,
    "updated_at": 1672574400
  }
  ```

#### 获取用户订阅状态

获取指定用户的当前订阅状态。

- **URL**: `/purchase/status/{user_id}/`
- **方法**: `GET`
- **权限**: 需要认证
- **响应**:
  ```json
  {
    "code": 200,
    "msg": "success",
    "data": {
      "has_active_subscription": true,
      "subscription_info": {
        "user_id": 123,
        "product_id": "Monthly_Subscription",
        "is_active": true,
        "is_successful": true,
        "purchase_date": "2023-01-01T12:00:00Z",
        "expires_at": "2023-02-01T12:00:00Z",
        "status": "success",
        "days_remaining": 30,
        "is_expired": false,
        "created_at": 1672574400,
        "updated_at": 1672574400
      }
    }
  }
  ```

## 错误响应

所有 API 在发生错误时将返回以下格式的响应：

```json
{
  "code": 400,
  "msg": "错误信息",
  "data": {}
}
```

常见错误码：

- 400: 请求参数错误
- 401: 未认证
- 403: 权限不足
- 404: 资源不存在
- 500: 服务器内部错误

## 认证

所有 API 请求需要在 HTTP 头部包含认证信息：
Authorization: {token}