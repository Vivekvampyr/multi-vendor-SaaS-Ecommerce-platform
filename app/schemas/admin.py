from pydantic import BaseModel, Field


class AdminDashboardStats(BaseModel):
    total_users: int = Field(default=0, description="Total registered users across all roles")
    total_admins: int = Field(default=0, description="Total platform administrators")
    total_vendors: int = Field(default=0, description="Total registered vendor accounts")
    total_customers: int = Field(default=0, description="Total registered customer accounts")
    total_plans: int = Field(default=0, description="Total SaaS plans created")
    total_active_plans: int = Field(default=0, description="Active SaaS plans available for vendors")
    total_subscriptions: int = Field(default=0, description="Total vendor subscriptions created")
    total_active_subscriptions: int = Field(default=0, description="Total currently active vendor subscriptions")

    # Financial & Revenue Metrics
    subscription_revenue: float = Field(default=0.0, description="Total active SaaS subscription recurring revenue (USD)")
    commission_revenue: float = Field(default=0.0, description="Total marketplace product sales commission earned (USD)")
    total_revenue: float = Field(default=0.0, description="Total combined platform revenue (Subscription + Commission) in USD")
    total_gmv: float = Field(default=0.0, description="Gross Merchandise Value (GMV) of all paid customer orders (USD)")
    total_vendor_payouts: float = Field(default=0.0, description="Total net vendor payouts after platform commission (USD)")
    total_paid_orders: int = Field(default=0, description="Total count of successfully paid orders")
    total_products_sold: int = Field(default=0, description="Total quantity of product units sold across all orders")
