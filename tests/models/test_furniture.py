import pytest

from src.models.furniture import Furniture


def test_furniture_from_dict_success():
    """
    필수 필드가 모두 포함된 딕셔너리가 주어졌을 때,
    Furniture 객체가 정상적으로 생성되는지 테스트합니다.
    """
    data = {
        "id": "test_id",
        "brand": "TestBrand",
        "name": "Test Furniture",
        "image_filename": "test.jpg",
        "price": 10000,
        "type": "Chair",
        "description": "A comfortable test chair.",
        "link": "http://example.com/test_chair",
        "color": "Red",
        "locations": ["Living Room", "Office"],
        "styles": ["Modern", "Minimalist"],
        "width": 50,
        "depth": 60,
        "height": 90,
        "seat_height": 45,
        "author": "tester",
        "created_at": "2024-07-30T12:00:00Z"
    }
    furniture = Furniture.from_dict(data)
    assert furniture.id == "test_id"
    assert furniture.brand == "TestBrand"
    assert furniture.name == "Test Furniture"
    assert furniture.image_filename == "test.jpg"
    assert furniture.price == 10000
    assert furniture.type == "Chair"
    assert furniture.description == "A comfortable test chair."
    assert furniture.link == "http://example.com/test_chair"
    assert furniture.color == "Red"
    assert furniture.locations == ["Living Room", "Office"]
    assert furniture.styles == ["Modern", "Minimalist"]
    assert furniture.width == 50
    assert furniture.depth == 60
    assert furniture.height == 90
    assert furniture.seat_height == 45
    assert furniture.author == "tester"
    assert furniture.created_at == "2024-07-30T12:00:00Z"

def test_furniture_from_dict_missing_required_field():
    """
    필수 필드가 누락된 딕셔너리가 주어졌을 때,
    ValueError가 발생하는지 테스트합니다.
    """
    data = {
        # 'id' 필드 누락
        "brand": "TestBrand",
        "name": "Test Furniture",
        "image_filename": "test.jpg",
        "price": 10000,
        "type": "Chair"
    }
    with pytest.raises(ValueError) as excinfo:
        Furniture.from_dict(data)
    assert "필수 필드가 누락되었습니다: id" in str(excinfo.value)

def test_furniture_from_dict_default_values():
    """
    선택적 필드가 누락된 딕셔너리가 주어졌을 때,
    기본값으로 Furniture 객체가 생성되는지 테스트합니다.
    """
    data = {
        "id": "default_test_id",
        "brand": "DefaultBrand",
        "name": "Default Furniture",
        "image_filename": "default.jpg",
        "price": 5000,
        "type": "Table"
    }
    furniture = Furniture.from_dict(data)
    assert furniture.id == "default_test_id"
    assert furniture.description == ""
    assert furniture.link == ""
    assert furniture.color == ""
    assert furniture.locations == []
    assert furniture.styles == []
    assert furniture.width == 0
    assert furniture.depth == 0
    assert furniture.height == 0
    assert furniture.seat_height is None
    assert furniture.author == ""
    assert furniture.created_at == "" 