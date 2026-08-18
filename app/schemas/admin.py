from pydantic import BaseModel, Field


class AdminDashboardStats(BaseModel):
    total_users: int = Field(description="Total registered users across all roles")
    total_admins: int = Field(description="Total platform administrators")
    total_vendors: int = Field(description="Total registered vendor accounts")
    total_customers: int = Field(description="Total registered customer accounts")
    total_plans: int = Field(description="Total SaaS plans created")
    total_active_plans: int = Field(description="Active SaaS plans available for vendors")
    total_subscriptions: int = Field(description="Total vendor subscriptions created")
    total_active_subscriptions: int = Field(description="Total currently active vendor subscriptions")
