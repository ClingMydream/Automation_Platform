import pytest

def total(price_cents,quantity):
    if type(quantity)is not int or quantity<=0:raise ValueError('quantity must be positive integer')
    return price_cents*quantity

@pytest.mark.parametrize('quantity',[0,-1,True])
def test_invalid_quantity(quantity):
    with pytest.raises(ValueError):total(2900,quantity)

def test_integer_amount():
    assert total(2900,2)==5800
