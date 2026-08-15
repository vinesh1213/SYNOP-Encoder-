from typing import Optional, Dict, Any
import logging
from .synop_encode import encode_synop

logger = logging.getLogger(__name__)

def generate_synop_message(data: Dict[str, Any], station_number: Optional[str]) -> Dict[str, Any]:
    """
    Wrapper around the modular synop_encode engine to format raw observations into a SYNOP message.
    
    Parameters
    ----------
    data : dict
        Observation data (must include manual indicators iR and iX).
    station_number : str or None
        5-digit WMO station number.
    """
    try:
        st_num = str(station_number) if station_number else "99999"
        result = encode_synop(data, st_num)
        
        if result.get("status") == "error":
            return {
                "synop": result.get("message", "SYNOP Generation Failed"),
                "explanations": {"Error": result.get("message")},
            }
            
        return {
            "synop": result.get("synop", ""),
            "explanations": result.get("explanations", {}),
        }
    except Exception as e:
        logger.error(f"Failed to generate SYNOP: {e}")
        return {
            "synop": f"SYNOP Generation Failed: Internal Error ({str(e)})",
            "explanations": {"Error": str(e)},
        }

