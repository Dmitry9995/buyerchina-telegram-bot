import requests
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SupplierInfo:
    company_name: str
    registration_status: str
    business_license: str
    years_in_business: int
    location: str
    main_products: str
    certifications: list
    risk_level: str
    verification_score: int
    contact_info: Dict[str, str]

class SupplierVerificationService:
    def __init__(self):
        self.mock_suppliers = {
            "shenzhen audio tech co": SupplierInfo(
                company_name="Shenzhen Audio Tech Co., Ltd",
                registration_status="✅ Verified",
                business_license="91440300MA5DC9XU8K",
                years_in_business=8,
                location="Shenzhen, Guangdong Province",
                main_products="Audio equipment, headphones, speakers",
                certifications=["ISO 9001", "CE", "FCC", "RoHS"],
                risk_level="🟢 Low Risk",
                verification_score=92,
                contact_info={
                    "email": "sales@szaudiotech.com",
                    "phone": "+86-755-8888-9999",
                    "website": "www.szaudiotech.com"
                }
            ),
            "guangzhou cable manufacturing": SupplierInfo(
                company_name="Guangzhou Cable Manufacturing Ltd",
                registration_status="✅ Verified",
                business_license="91440101MA5EF2RT7P",
                years_in_business=12,
                location="Guangzhou, Guangdong Province",
                main_products="USB cables, charging cables, data cables",
                certifications=["ISO 9001", "CE", "UL", "MFi"],
                risk_level="🟢 Low Risk",
                verification_score=88,
                contact_info={
                    "email": "info@gzcable.com",
                    "phone": "+86-20-1234-5678",
                    "website": "www.gzcable.com"
                }
            ),
            "dongguan plastic industries": SupplierInfo(
                company_name="Dongguan Plastic Industries Co.",
                registration_status="⚠️ Pending Verification",
                business_license="91441900MA4WK8XL2N",
                years_in_business=5,
                location="Dongguan, Guangdong Province",
                main_products="Phone cases, plastic accessories",
                certifications=["ISO 9001", "CE"],
                risk_level="🟡 Medium Risk",
                verification_score=75,
                contact_info={
                    "email": "sales@dgplastic.cn",
                    "phone": "+86-769-8765-4321",
                    "website": "www.dgplastic.cn"
                }
            )
        }
    
    def verify_supplier(self, company_name: str) -> Optional[SupplierInfo]:
        """Verify a supplier by company name"""
        company_key = company_name.lower().strip()
        
        # Check exact matches first
        if company_key in self.mock_suppliers:
            return self.mock_suppliers[company_key]
        
        # Check partial matches
        for key, supplier in self.mock_suppliers.items():
            if company_key in key or key in company_key:
                return supplier
        
        return None
    
    def format_verification_report(self, supplier: SupplierInfo, language_service=None, user_id=None) -> str:
        """Format supplier verification into a readable report"""
        if language_service and user_id:
            header = language_service.get_text(user_id, 'verification_report')
            company_label = language_service.get_text(user_id, 'company')
            status_label = language_service.get_text(user_id, 'status')
            location_label = language_service.get_text(user_id, 'location')
        else:
            header = "🏢 **Supplier Verification Report**"
            company_label = "Company:"
            status_label = "Status:"
            location_label = "Location:"
        
        report = f"{header}\n\n"
        report += f"**{company_label}** {supplier.company_name}\n"
        report += f"**{status_label}** {supplier.registration_status}\n"
        report += f"**License:** {supplier.business_license}\n"
        report += f"**Experience:** {supplier.years_in_business} years\n"
        report += f"**{location_label}** {supplier.location}\n"
        report += f"**Risk Level:** {supplier.risk_level}\n"
        report += f"**Score:** {supplier.verification_score}/100\n\n"
        
        report += f"**Main Products:**\n{supplier.main_products}\n\n"
        
        report += f"**Certifications:**\n"
        for cert in supplier.certifications:
            report += f"• {cert}\n"
        
        report += f"\n**Contact Information:**\n"
        report += f"📧 {supplier.contact_info.get('email', 'N/A')}\n"
        report += f"📞 {supplier.contact_info.get('phone', 'N/A')}\n"
        report += f"🌐 {supplier.contact_info.get('website', 'N/A')}\n"
        
        report += f"\n💡 *Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
        
        return report
    
    def get_risk_assessment(self, supplier: SupplierInfo, language_service=None, user_id=None) -> str:
        """Get detailed risk assessment"""
        if language_service and user_id:
            header = language_service.get_text(user_id, 'risk_assessment', name=supplier.company_name)
        else:
            header = f"🔍 **Risk Assessment for {supplier.company_name}**"
        
        assessment = f"{header}\n\n"
        
        if supplier.verification_score >= 85:
            if language_service and user_id:
                title = language_service.get_text(user_id, 'recommended_supplier')
            else:
                title = "✅ **Recommended Supplier**"
            assessment += f"{title}\n"
            assessment += "• High verification score\n"
            assessment += "• Strong business credentials\n"
            assessment += "• Low risk for business partnership\n"
        elif supplier.verification_score >= 70:
            if language_service and user_id:
                title = language_service.get_text(user_id, 'proceed_caution')
            else:
                title = "⚠️ **Proceed with Caution**"
            assessment += f"{title}\n"
            assessment += "• Moderate verification score\n"
            assessment += "• Additional due diligence recommended\n"
            assessment += "• Consider requesting additional documentation\n"
        else:
            if language_service and user_id:
                title = language_service.get_text(user_id, 'high_risk')
            else:
                title = "❌ **High Risk - Not Recommended**"
            assessment += f"{title}\n"
            assessment += "• Low verification score\n"
            assessment += "• Significant risk factors identified\n"
            assessment += "• Recommend finding alternative suppliers\n"
        
        return assessment
