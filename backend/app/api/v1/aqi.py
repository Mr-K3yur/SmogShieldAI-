from fastapi import APIRouter
from app.schemas.aqi import AQICalculationRequest, OverallAQIResult
from app.core.cpcb_naqi import compute_station_cpcb_aqi

router = APIRouter(prefix="/aqi", tags=["Air Quality Calculation Engine"])


@router.post("/calculate", response_model=OverallAQIResult)
async def calculate_cpcb_aqi(request: AQICalculationRequest) -> OverallAQIResult:
    """Calculate CPCB National AQI, individual sub-indices, and category classification.

    Adheres strictly to the official CPCB 2014 linear segmentation formula, minimum data criteria
    (at least 3 pollutants, at least 1 particulate), and dominant pollutant assignment.
    """
    result_dict = compute_station_cpcb_aqi(request.measurements)
    return OverallAQIResult(**result_dict)
