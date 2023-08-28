from django.db import models
from django.db import models
from typing import TypeVar, Any


_QS = TypeVar("_QS", bound="models._BaseQuerySet[Any]")