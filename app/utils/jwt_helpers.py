"""JWT操作関連ユーティリティ

JWT トークンの生成、検証、エンコード処理を提供
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

# JWT トークンタイプ定数（Lint警告回避のため設定: 実際は問題ない）
TOKEN_TYPE_ACCESS = "access"  # nosec B105  # noqa: S105
TOKEN_TYPE_REFRESH = "refresh"  # nosec B105 # noqa: S105
TOKEN_TYPE_PASSWORD_RESET = "password_reset"  # nosec B105 # noqa: S105


def encode_jwt_token(payload: dict[str, Any], secret_key: str, algorithm: str) -> str:
    """JWT トークンエンコード

    PyJWT のバージョン間での bytes/str 戻り値の違いを吸収

    Args:
        payload: エンコードするペイロード
        secret_key: 署名用秘密鍵
        algorithm: 署名アルゴリズム

    Returns:
        エンコードされたJWT文字列

    Raises:
        RuntimeError: エンコードに失敗した場合
    """
    try:
        encoded_jwt_raw = jwt.encode(payload, secret_key, algorithm=algorithm)
        # PyJWTのバージョンによってbytesまたはstrが返される可能性があるため変換
        return encoded_jwt_raw.decode("utf-8") if isinstance(encoded_jwt_raw, bytes) else encoded_jwt_raw
    except Exception as e:
        raise RuntimeError(f"JWTトークン生成に失敗しました: {e}") from e


def decode_jwt_token(token: str, secret_key: str, algorithm: str, verify_exp: bool = True) -> dict[str, Any]:
    """JWT トークンデコード

    Args:
        token: デコード対象のJWT文字列
        secret_key: 検証用秘密鍵
        algorithm: 検証アルゴリズム
        verify_exp: 有効期限を検証するか

    Returns:
        デコードされたペイロード

    Raises:
        jwt.ExpiredSignatureError: トークンの有効期限切れ
        jwt.InvalidTokenError: 無効なトークン
    """
    options = {"verify_exp": verify_exp} if not verify_exp else {}
    decoded_result: dict[str, Any] = jwt.decode(token, secret_key, algorithms=[algorithm], options=options)
    return decoded_result


def validate_token_type(payload: dict[str, Any], expected_type: str) -> bool:
    """トークンタイプ検証

    Args:
        payload: デコード済みペイロード
        expected_type: 期待されるトークンタイプ

    Returns:
        トークンタイプが一致する場合True
    """
    return payload.get("type") == expected_type


def extract_user_id_from_token(payload: dict[str, Any]) -> str:
    """トークンからユーザーID抽出

    Args:
        payload: デコード済みペイロード

    Returns:
        ユーザーID文字列

    Raises:
        ValueError: ユーザーIDが無効な場合
    """
    user_id_raw = payload.get("sub")
    if user_id_raw is None or not isinstance(user_id_raw, str):
        raise ValueError("無効なユーザーIDです")

    user_id_result: str = user_id_raw
    return user_id_result


def extract_jti_from_token(payload: dict[str, Any]) -> str:
    """トークンからJTI（JWT ID）抽出

    Args:
        payload: デコード済みペイロード

    Returns:
        JTI文字列

    Raises:
        ValueError: JTIが無効な場合
    """
    jti_raw = payload.get("jti")
    if not jti_raw or not isinstance(jti_raw, str):
        raise ValueError("無効なトークン形式です（JTIがありません）")

    jti_result: str = jti_raw
    return jti_result


def create_token_payload(
    user_id: str, token_type: str, expires_delta: timedelta, additional_claims: dict[str, Any] | None = None
) -> dict[str, Any]:
    """JWTペイロード作成

    Args:
        user_id: ユーザーID
        token_type: トークンタイプ
        expires_delta: 有効期限
        additional_claims: 追加のクレーム

    Returns:
        JWT ペイロード
    """
    now = datetime.now(UTC)
    expire = now + expires_delta
    jti = str(uuid.uuid4())

    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "jti": jti,
        "type": token_type,
    }

    # 追加クレームのマージ
    if additional_claims:
        payload.update(additional_claims)

    return payload


def create_access_token_payload(
    user_id: str, expires_delta: timedelta, additional_claims: dict[str, Any] | None = None
) -> dict[str, Any]:
    """アクセストークン用ペイロード作成

    Args:
        user_id: ユーザーID
        expires_delta: 有効期限
        additional_claims: 追加のクレーム

    Returns:
        アクセストークン用ペイロード
    """
    return create_token_payload(user_id, TOKEN_TYPE_ACCESS, expires_delta, additional_claims)


def create_refresh_token_payload(user_id: str, expires_delta: timedelta) -> dict[str, Any]:
    """リフレッシュトークン用ペイロード作成

    Args:
        user_id: ユーザーID
        expires_delta: 有効期限

    Returns:
        リフレッシュトークン用ペイロード
    """
    return create_token_payload(user_id, TOKEN_TYPE_REFRESH, expires_delta)


def create_password_reset_token_payload(user_id: str, expires_delta: timedelta) -> dict[str, Any]:
    """パスワードリセットトークン用ペイロード作成

    Args:
        user_id: ユーザーID
        expires_delta: 有効期限

    Returns:
        パスワードリセットトークン用ペイロード
    """
    return create_token_payload(user_id, TOKEN_TYPE_PASSWORD_RESET, expires_delta)


class JWTHelper:
    """JWT操作ヘルパークラス

    設定値を保持してJWT操作を簡単に行うためのクラス
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def encode(self, payload: dict[str, Any]) -> str:
        """トークンエンコード"""
        return encode_jwt_token(payload, self.secret_key, self.algorithm)

    def decode(self, token: str, verify_exp: bool = True) -> dict[str, Any]:
        """トークンデコード"""
        return decode_jwt_token(token, self.secret_key, self.algorithm, verify_exp)

    def create_access_token(
        self, user_id: str, expires_delta: timedelta, additional_claims: dict[str, Any] | None = None
    ) -> str:
        """アクセストークン作成"""
        payload = create_access_token_payload(user_id, expires_delta, additional_claims)
        return self.encode(payload)

    def create_refresh_token(self, user_id: str, expires_delta: timedelta) -> str:
        """リフレッシュトークン作成"""
        payload = create_refresh_token_payload(user_id, expires_delta)
        return self.encode(payload)

    def create_password_reset_token(self, user_id: str, expires_delta: timedelta) -> str:
        """パスワードリセットトークン作成"""
        payload = create_password_reset_token_payload(user_id, expires_delta)
        return self.encode(payload)

    def verify_access_token(self, token: str) -> str:
        """アクセストークン検証

        Args:
            token: 検証対象のトークン

        Returns:
            ユーザーID

        Raises:
            ValueError: トークンタイプが不正な場合
            jwt.ExpiredSignatureError: トークンの有効期限切れ
            jwt.InvalidTokenError: 無効なトークン
        """
        payload = self.decode(token)

        if not validate_token_type(payload, TOKEN_TYPE_ACCESS):
            raise ValueError("無効なトークンタイプです")

        return extract_user_id_from_token(payload)

    def verify_refresh_token(self, token: str) -> str:
        """リフレッシュトークン検証

        Args:
            token: 検証対象のトークン

        Returns:
            ユーザーID

        Raises:
            ValueError: トークンタイプが不正な場合
            jwt.ExpiredSignatureError: トークンの有効期限切れ
            jwt.InvalidTokenError: 無効なトークン
        """
        payload = self.decode(token)

        if not validate_token_type(payload, TOKEN_TYPE_REFRESH):
            raise ValueError("無効なトークンタイプです")

        return extract_user_id_from_token(payload)

    def verify_password_reset_token(self, token: str) -> str:
        """パスワードリセットトークン検証

        Args:
            token: 検証対象のトークン

        Returns:
            ユーザーID

        Raises:
            ValueError: トークンタイプが不正な場合
            jwt.ExpiredSignatureError: トークンの有効期限切れ
            jwt.InvalidTokenError: 無効なトークン
        """
        payload = self.decode(token)

        if not validate_token_type(payload, TOKEN_TYPE_PASSWORD_RESET):
            raise ValueError("無効なトークンタイプです")

        return extract_user_id_from_token(payload)

    def extract_jti(self, token: str) -> str:
        """トークンからJTI抽出（ブラックリスト用）

        Args:
            token: 対象のトークン

        Returns:
            JTI文字列
        """
        payload = self.decode(token, verify_exp=False)  # 期限切れでもJTIは取得
        return extract_jti_from_token(payload)


def create_jwt_helper(secret_key: str, algorithm: str = "HS256") -> JWTHelper:
    """JWTHelperファクトリ関数

    Args:
        secret_key: JWT署名用秘密鍵
        algorithm: 署名アルゴリズム

    Returns:
        JWTHelperインスタンス
    """
    return JWTHelper(secret_key, algorithm)
