#!/usr/bin/env python3

from . import Request, Response, request_type, response_type
from ..types import RFPStatDataType


@request_type
class GetRFPStatistic(Request):
    FIELDS = {
        "id": int,
        "maxRecords": int,
        "recordSet": int,
    }


@response_type
class GetRFPStatisticResp(Response):
    CHILDS = {
        "rfpStatData": RFPStatDataType,
    }
