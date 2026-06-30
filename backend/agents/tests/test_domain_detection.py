import pytest
from unittest.mock import AsyncMock, patch
from backend.agents.domain_detection import DomainDetectionModule
from backend.agents.schemas import BusinessDomainDetection

@pytest.mark.asyncio
async def test_domain_detection_success():
    module = DomainDetectionModule()
    
    # Mock LLMClient response
    mock_response = {
        "primary_domain": "Healthcare",
        "secondary_domains": ["FinTech"],
        "confidence": 98
    }
    
    with patch.object(module.llm_client, "generate_json", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_response
        
        result = await module.detect_domain("Some medical and billing requirements...")
        
        assert isinstance(result, BusinessDomainDetection)
        assert result.primary_domain == "Healthcare"
        assert "FinTech" in result.secondary_domains
        assert result.confidence == 98

@pytest.mark.asyncio
async def test_domain_detection_fallback():
    module = DomainDetectionModule()
    
    # Mock LLMClient to raise an exception, forcing fallback
    with patch.object(module.llm_client, "generate_json", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = Exception("LLM Error")
        
        # This text contains keywords for E-Commerce and Retail
        text = "Develop a shopping cart checkout system with product inventory management for retail stores."
        result = await module.detect_domain(text)
        
        assert isinstance(result, BusinessDomainDetection)
        assert result.primary_domain in ["E-Commerce", "Retail"]
        assert result.confidence == 80

def test_fallback_keyword_detection_hrms():
    module = DomainDetectionModule()
    
    # Text with HRMS keywords
    text = "The employee shall submit a leave request to the HR manager."
    result = module._fallback_keyword_detection(text)
    
    assert result.primary_domain == "HRMS"
    assert result.confidence == 80
