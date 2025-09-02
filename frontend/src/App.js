import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

/** =========================
 *  API base + axios instance
 *  ========================= */
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API_BASE });

// attach token automatically
api.interceptors.request.use((config) => {
  const t = localStorage.getItem("token");
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});



/** =========================
 *  Small Auth helpers
 *  ========================= */
function saveToken(tok) {
  localStorage.setItem("token", tok);
}
function clearToken() {
  localStorage.removeItem("token");
}
function getToken() {
  return localStorage.getItem("token");
}

/** =========================
 *  Login screen
 *  ========================= */
function Login({ onSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      // backend expects x-www-form-urlencoded with fields: username, password
      const body = new URLSearchParams();
      body.set("username", email);
      body.set("password", password);

      const res = await axios.post(`${API_BASE}/auth/login`, body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      const tok = res.data?.access_token;
      if (!tok) throw new Error("No token");
      saveToken(tok);
      onSuccess(tok);
    } catch (e) {
      setErr("Incorrect email or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 p-6">
      <form onSubmit={submit} className="bg-white p-6 rounded-lg shadow w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-bold">Sign in to Fitforxe</h1>
        {err && <div className="text-red-600 text-sm">{err}</div>}
        <input
          type="email"
          placeholder="Email"
          className="w-full p-3 border rounded"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          className="w-full p-3 border rounded"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-3 rounded hover:bg-blue-700"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}

/** =========================
 *  Checkout Page Component
 *  ========================= */
const CheckoutPage = ({ memberData, onNavigate, onClose }) => {
  const [paymentGateway, setPaymentGateway] = useState("stripe");
  const [userCountry, setUserCountry] = useState("US");
  const [isLoading, setIsLoading] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState(null);
  const [formData, setFormData] = useState({
    name: memberData?.name || "",
    email: memberData?.email || "",
    phone: memberData?.phone || "",
    country: "",
    membership_plan: "basic",
  });

  const membershipPlans = {
    basic: { name: "Basic", price: 29.99, features: ["Gym Access", "Basic Equipment", "Locker Room"] },
    premium: { name: "Premium", price: 49.99, features: ["Gym Access", "All Equipment", "Group Classes", "Locker Room"] },
    vip: { name: "VIP", price: 79.99, features: ["All Premium Features", "Personal Training", "Priority Support", "Premium Locker"] },
  };

  useEffect(() => {
    detectCountry();
  }, []);

  const detectCountry = async () => {
    try {
      const response = await api.get(`/detect-country`);
      const country = response.data.country;
      setUserCountry(country);
      setFormData((prev) => ({ ...prev, country }));
      setPaymentGateway(country === "IN" ? "razorpay" : "stripe");
    } catch (error) {
      console.error("Error detecting country:", error);
      setPaymentGateway("stripe");
    }
  };

  const handlePayment = async () => {
    setIsLoading(true);
    setPaymentStatus(null);

    try {
      if (paymentGateway === "razorpay") {
        await processRazorpayPayment();
      } else {
        await processStripePayment();
      }
    } catch (error) {
      console.error("Payment error:", error);
      setPaymentStatus({
        type: "error",
        message: "Payment processing failed. Please try again.",
      });
    }
    setIsLoading(false);
  };

  const processRazorpayPayment = async () => {
    try {
      // Create member first if not exists
      let memberId = memberData?.id;
      if (!memberId) {
        const memberResponse = await api.post(`/members`, {
          first_name: formData.name.split(" ")[0],
          last_name: formData.name.split(" ").slice(1).join(" ") || "Member",
          email: formData.email,
          phone: formData.phone,
          membership_type: formData.membership_plan,
          enable_auto_billing: true,
        });
        memberId = memberResponse.data.id;
      }

      // Create Razorpay order
      const orderResponse = await api.post(`/razorpay/create-order`, {
        member_id: memberId,
        membership_type: formData.membership_plan,
        customer_name: formData.name,
        customer_email: formData.email,
        customer_phone: formData.phone,
        customer_country: formData.country,
      });

      const { order_id, amount, razorpay_key_id } = orderResponse.data;

      const options = {
        key: razorpay_key_id,
        amount: amount * 100,
        currency: "INR",
        name: "FitForce Gym",
        description: `${membershipPlans[formData.membership_plan].name} Membership`,
        order_id,
        handler: async (response) => {
          try {
            await api.post(`/razorpay/verify-payment`, {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            setPaymentStatus({ type: "success", message: "Payment successful! Welcome to FitForce!" });
          } catch {
            setPaymentStatus({ type: "error", message: "Payment verification failed. Please contact support." });
          }
        },
        prefill: { name: formData.name, email: formData.email, contact: formData.phone },
        theme: { color: "#3B82F6" },
        modal: {
          ondismiss: () => setPaymentStatus({ type: "error", message: "Payment was cancelled." }),
        },
      };

      if (window.Razorpay) {
        new window.Razorpay(options).open();
      } else {
        const script = document.createElement("script");
        script.src = "https://checkout.razorpay.com/v1/checkout.js";
        script.onload = () => new window.Razorpay(options).open();
        document.body.appendChild(script);
      }
    } catch (error) {
      console.error("Razorpay payment error:", error);
      throw error;
    }
  };

  const processStripePayment = async () => {
    try {
      let memberId = memberData?.id;
      if (!memberId) {
        const memberResponse = await api.post(`/members`, {
          first_name: formData.name.split(" ")[0],
          last_name: formData.name.split(" ").slice(1).join(" ") || "Member",
          email: formData.email,
          phone: formData.phone,
          membership_type: formData.membership_plan,
          enable_auto_billing: true,
        });
        memberId = memberResponse.data.id;
      }

      const currentUrl = window.location.origin + window.location.pathname;
      const stripeResponse = await api.post(`/stripe/checkout`, {
        member_id: memberId,
        membership_type: formData.membership_plan,
        success_url: `${currentUrl}?payment_success=true&session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${currentUrl}?payment_cancelled=true`,
      });

      window.location.href = stripeResponse.data.url;
    } catch (error) {
      console.error("Stripe payment error:", error);
      throw error;
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-screen overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b p-6 flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">Join FitForce</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 text-2xl">×</button>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left Column - Customer Information */}
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Your Information</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                    <input
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
                    <select
                      value={formData.country}
                      onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="IN">India</option>
                      <option value="US">United States</option>
                      <option value="GB">United Kingdom</option>
                      <option value="CA">Canada</option>
                      <option value="AU">Australia</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Payment Method Selection */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Payment Method</h3>
                <div className="space-y-3">
                  <div className="flex items-center p-3 border border-gray-200 rounded-lg">
                    <input
                      type="radio"
                      id="razorpay"
                      name="payment_gateway"
                      value="razorpay"
                      checked={paymentGateway === "razorpay"}
                      onChange={(e) => setPaymentGateway(e.target.value)}
                      className="mr-3"
                    />
                    <label htmlFor="razorpay" className="flex items-center flex-grow">
                      <div className="flex items-center space-x-2">
                        <div className="w-8 h-8 bg-blue-600 rounded flex items-center justify-center text-white font-bold text-xs">RP</div>
                        <div>
                          <div className="font-medium">Razorpay</div>
                          <div className="text-sm text-gray-500">UPI, Cards, NetBanking (India)</div>
                        </div>
                      </div>
                      {userCountry === "IN" && (
                        <span className="ml-auto bg-green-100 text-green-800 text-xs px-2 py-1 rounded">Recommended</span>
                      )}
                    </label>
                  </div>

                  <div className="flex items-center p-3 border border-gray-200 rounded-lg">
                    <input
                      type="radio"
                      id="stripe"
                      name="payment_gateway"
                      value="stripe"
                      checked={paymentGateway === "stripe"}
                      onChange={(e) => setPaymentGateway(e.target.value)}
                      className="mr-3"
                    />
                    <label htmlFor="stripe" className="flex items-center flex-grow">
                      <div className="flex items-center space-x-2">
                        <div className="w-8 h-8 bg-purple-600 rounded flex items-center justify-center text-white font-bold text-xs">ST</div>
                        <div>
                          <div className="font-medium">Stripe</div>
                          <div className="text-sm text-gray-500">Credit/Debit Cards (International)</div>
                        </div>
                      </div>
                      {userCountry !== "IN" && (
                        <span className="ml-auto bg-green-100 text-green-800 text-xs px-2 py-1 rounded">Recommended</span>
                      )}
                    </label>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column - Membership Plans */}
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Choose Your Plan</h3>
                <div className="space-y-4">
                  {Object.entries(membershipPlans).map(([planKey, plan]) => (
                    <div
                      key={planKey}
                      className={`border rounded-lg p-4 cursor-pointer transition-all ${
                        formData.membership_plan === planKey ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-gray-300"
                      }`}
                      onClick={() => setFormData({ ...formData, membership_plan: planKey })}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          <input type="radio" value={planKey} checked={formData.membership_plan === planKey} readOnly className="mr-3" />
                          <div>
                            <div className="font-semibold text-gray-900">{plan.name}</div>
                            <div className="text-sm text-gray-600">{plan.features.join(" • ")}</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-xl font-bold text-gray-900">
                            {paymentGateway === "razorpay" ? "₹" : "$"}
                            {paymentGateway === "razorpay" ? (plan.price * 83).toFixed(0) : plan.price}
                          </div>
                          <div className="text-sm text-gray-500">/month</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Payment Status */}
              {paymentStatus && (
                <div className={`p-4 rounded-lg ${paymentStatus.type === "success" ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"}`}>
                  <div className="flex items-center">
                    {paymentStatus.type === "success" ? (
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    )}
                    {paymentStatus.message}
                  </div>
                </div>
              )}

              {/* Payment Button */}
              <button
                onClick={handlePayment}
                disabled={isLoading || !formData.name || !formData.email || !formData.phone}
                className={`w-full py-4 px-6 rounded-lg font-semibold text-white transition-all ${
                  isLoading || !formData.name || !formData.email || !formData.phone
                    ? "bg-gray-400 cursor-not-allowed"
                    : paymentGateway === "razorpay"
                    ? "bg-blue-600 hover:bg-blue-700"
                    : "bg-purple-600 hover:bg-purple-700"
                }`}
              >
                {isLoading ? (
                  <div className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Processing...
                  </div>
                ) : (
                  `Pay ${paymentGateway === "razorpay" ? "₹" : "$"}${
                    paymentGateway === "razorpay" ? (membershipPlans[formData.membership_plan].price * 83).toFixed(0) : membershipPlans[formData.membership_plan].price
                  } with ${paymentGateway === "razorpay" ? "Razorpay" : "Stripe"}`
                )}
              </button>

              <div className="text-center text-sm text-gray-500">
                <div className="flex items-center justify-center space-x-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                  <span>Secure payment processing</span>
                </div>
                <p className="mt-1">Your payment information is encrypted and secure</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/** =========================
 *  Profile Management
 *  ========================= */
const ProfileManagement = ({ onNavigate }) => {
  const [profile, setProfile] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    gym_name: "FitForce",
    owner_name: "",
    email: "",
    phone: "",
    address: "",
    city: "",
    state: "",
    zip_code: "",
  });

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await api.get(`/profile`);
      setProfile(response.data);
      setFormData({
        gym_name: response.data.gym_name || "FitForce",
        owner_name: response.data.owner_name || "",
        email: response.data.email || "",
        phone: response.data.phone || "",
        address: response.data.address || "",
        city: response.data.city || "",
        state: response.data.state || "",
        zip_code: response.data.zip_code || "",
      });
    } catch (error) {
      console.error("Error fetching profile:", error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (profile && profile.id) {
        await api.put(`/profile`, formData);
      } else {
        await api.post(`/profile`, formData);
      }
      setIsEditing(false);
      fetchProfile();
      alert("Profile updated successfully!");
    } catch (error) {
      console.error("Error updating profile:", error);
      alert("Error updating profile. Please try again.");
    }
  };

  if (!profile) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <h2 className="text-2xl font-bold text-gray-900">Gym Owner Profile</h2>
        <button onClick={() => setIsEditing(!isEditing)} className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
          {isEditing ? "Cancel" : "Edit Profile"}
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6 lg:p-8">
        {isEditing ? (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[
                ["Gym Name", "gym_name"],
                ["Owner Name", "owner_name"],
                ["Email", "email"],
                ["Phone", "phone"],
                ["Address", "address"],
                ["City", "city"],
                ["State", "state"],
                ["Zip Code", "zip_code"],
              ].map(([label, key]) => (
                <div key={key} className={["address"].includes(key) ? "md:col-span-2" : ""}>
                  <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
                  <input
                    type={key === "email" ? "email" : "text"}
                    value={formData[key]}
                    onChange={(e) => setFormData({ ...formData, [key]: e.target.value })}
                    className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
              ))}
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
              <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                Save Changes
              </button>
              <button type="button" onClick={() => setIsEditing(false)} className="bg-gray-500 text-white px-6 py-2 rounded-lg hover:bg-gray-600 transition-colors">
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Gym Information</h3>
                <div className="space-y-2">
                  <p>
                    <span className="font-medium">Gym Name:</span> {profile.gym_name}
                  </p>
                  <p>
                    <span className="font-medium">Owner:</span> {profile.owner_name}
                  </p>
                  <p>
                    <span className="font-medium">Email:</span> {profile.email}
                  </p>
                  <p>
                    <span className="font-medium">Phone:</span> {profile.phone}
                  </p>
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Address</h3>
                <div className="space-y-2">
                  <p>{profile.address}</p>
                  <p>
                    {profile.city}, {profile.state} {profile.zip_code}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/** =========================
 *  Member Management
 *  ========================= */
const MemberManagement = ({ onNavigate }) => {
  const [members, setMembers] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showCheckout, setShowCheckout] = useState(false);
  const [editingMember, setEditingMember] = useState(null);
  const [membershipPricing, setMembershipPricing] = useState({});
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    membership_type: "basic",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    medical_conditions: "",
    enable_auto_billing: false,
    card_holder_name: "",
    card_number: "",
    expiry_date: "",
    cvv: "",
  });

  useEffect(() => {
    fetchMembers();
    fetchMembershipPricing();
  }, []);

  const fetchMembers = async () => {
    try {
      const response = await api.get(`/members`);
      setMembers(response.data);
    } catch (error) {
      console.error("Error fetching members:", error);
    }
  };

  const fetchMembershipPricing = async () => {
    try {
      const response = await api.get(`/membership-pricing`);
      setMembershipPricing(response.data);
    } catch (error) {
      console.error("Error fetching pricing:", error);
    }
  };

  // Credit card helpers (kept for UI only)
  const formatCardNumber = (value) => {
    const v = value.replace(/\s+/g, "").replace(/[^0-9]/gi, "");
    const matches = v.match(/\d{4,16}/g);
    const match = (matches && matches[0]) || "";
    const parts = [];
    for (let i = 0, len = match.length; i < len; i += 4) parts.push(match.substring(i, i + 4));
    return parts.length ? parts.join(" ") : v;
  };
  const formatExpiryDate = (value) => {
    const v = value.replace(/\s+/g, "").replace(/[^0-9]/gi, "");
    return v.length >= 2 ? v.substring(0, 2) + "/" + v.substring(2, 4) : v;
  };
  const handleCardInputChange = (field, value) => {
    let formattedValue = value;
    if (field === "card_number") formattedValue = formatCardNumber(value);
    else if (field === "expiry_date") formattedValue = formatExpiryDate(value);
    else if (field === "cvv") formattedValue = value.replace(/[^0-9]/g, "");
    setFormData({ ...formData, [field]: formattedValue });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!editingMember && formData.enable_auto_billing) {
      setShowCheckout(true);
      return;
    }
    try {
      if (editingMember) {
        await api.put(`/members/${editingMember.id}`, formData);
      } else {
        await api.post(`/members`, formData);
      }
      resetForm();
      setShowAddForm(false);
      setEditingMember(null);
      fetchMembers();
    } catch (error) {
      console.error("Error saving member:", error);
      alert("Error saving member. Please try again.");
    }
  };

  const resetForm = () => {
    setFormData({
      first_name: "",
      last_name: "",
      email: "",
      phone: "",
      membership_type: "basic",
      emergency_contact_name: "",
      emergency_contact_phone: "",
      medical_conditions: "",
      enable_auto_billing: false,
      card_holder_name: "",
      card_number: "",
      expiry_date: "",
      cvv: "",
    });
  };

  const handleEdit = (member) => {
    setEditingMember(member);
    setFormData({
      first_name: member.first_name,
      last_name: member.last_name,
      email: member.email,
      phone: member.phone,
      membership_type: member.membership_type,
      emergency_contact_name: member.emergency_contact_name || "",
      emergency_contact_phone: member.emergency_contact_phone || "",
      medical_conditions: member.medical_conditions || "",
      enable_auto_billing: member.auto_billing_enabled || false,
      card_holder_name: "",
      card_number: "",
      expiry_date: "",
      cvv: "",
    });
    setShowAddForm(true);
  };

  const handleDelete = async (memberId) => {
    if (window.confirm("Are you sure you want to delete this member?")) {
      try {
        await api.delete(`/members/${memberId}`);
        fetchMembers();
      } catch (error) {
        console.error("Error deleting member:", error);
      }
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "active":
        return "bg-green-100 text-green-800";
      case "inactive":
        return "bg-gray-100 text-gray-800";
      case "expired":
        return "bg-red-100 text-red-800";
      case "suspended":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getMembershipColor = (type) => {
    switch (type) {
      case "basic":
        return "bg-blue-100 text-blue-800";
      case "premium":
        return "bg-purple-100 text-purple-800";
      case "vip":
        return "bg-gold-100 text-gold-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <h2 className="text-2xl font-bold text-gray-900">Member Management</h2>
        <button onClick={() => setShowAddForm(true)} className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
          Add New Member
        </button>
      </div>

      {showCheckout && (
        <CheckoutPage
          memberData={{ name: `${formData.first_name} ${formData.last_name}`, email: formData.email, phone: formData.phone }}
          onNavigate={onNavigate}
          onClose={() => {
            setShowCheckout(false);
            setShowAddForm(false);
            resetForm();
            fetchMembers();
          }}
        />
      )}

      {showAddForm && !showCheckout && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-40 p-4">
          <div className="bg-white p-6 lg:p-8 rounded-lg max-w-2xl w-full max-h-screen overflow-y-auto">
            <h3 className="text-xl font-bold mb-6">{editingMember ? "Edit Member" : "Add New Member"}</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="First Name"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  className="p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
                <input
                  type="text"
                  placeholder="Last Name"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  className="p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>
              <input
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
              <input
                type="tel"
                placeholder="Phone"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Membership Type</label>
                <select
                  value={formData.membership_type}
                  onChange={(e) => setFormData({ ...formData, membership_type: e.target.value })}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="basic">Basic - ${membershipPricing.basic}/month</option>
                  <option value="premium">Premium - ${membershipPricing.premium}/month</option>
                  <option value="vip">VIP - ${membershipPricing.vip}/month</option>
                </select>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Emergency Contact Name"
                  value={formData.emergency_contact_name}
                  onChange={(e) => setFormData({ ...formData, emergency_contact_name: e.target.value })}
                  className="p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <input
                  type="tel"
                  placeholder="Emergency Contact Phone"
                  value={formData.emergency_contact_phone}
                  onChange={(e) => setFormData({ ...formData, emergency_contact_phone: e.target.value })}
                  className="p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <textarea
                placeholder="Medical Conditions (Optional)"
                value={formData.medical_conditions}
                onChange={(e) => setFormData({ ...formData, medical_conditions: e.target.value })}
                className="w-full p-3 border rounded-lg h-24 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              {!editingMember && (
                <div className="bg-blue-50 p-4 rounded-lg">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.enable_auto_billing}
                      onChange={(e) => setFormData({ ...formData, enable_auto_billing: e.target.checked })}
                      className="mr-3"
                    />
                    <span className="text-sm">
                      <strong>Enable Auto-Billing</strong> - Set up automatic monthly payments
                    </span>
                  </label>
                  {formData.enable_auto_billing && (
                    <p className="text-sm text-blue-600 mt-2">
                      You'll be redirected to our secure payment page to complete the setup with dual payment options (Stripe/Razorpay).
                    </p>
                  )}
                </div>
              )}
              <div className="flex flex-col sm:flex-row gap-4">
                <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                  {editingMember ? "Update Member" : "Continue"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddForm(false);
                    setEditingMember(null);
                    resetForm();
                  }}
                  className="bg-gray-500 text-white px-6 py-2 rounded-lg hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden sm:table-cell">Phone</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Membership</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden lg:table-cell">Auto-Billing</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {members.map((member) => (
                <tr key={member.id}>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{member.first_name} {member.last_name}</div>
                  </td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <div className="truncate max-w-32">{member.email}</div>
                  </td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden sm:table-cell">
                    {member.phone}
                  </td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getMembershipColor(member.membership_type)}`}>
                      {member.membership_type.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(member.status)}`}>
                      {member.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden lg:table-cell">
                    {member.auto_billing_enabled ? <span className="text-green-600">✓ Enabled</span> : <span className="text-gray-400">Disabled</span>}
                  </td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm space-x-2">
                    <button onClick={() => handleEdit(member)} className="text-blue-600 hover:text-blue-900">Edit</button>
                    <button onClick={() => handleDelete(member.id)} className="text-red-600 hover:text-red-900">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

/** =========================
 *  Payment Management
 *  ========================= */
const PaymentManagement = ({ onNavigate }) => {
  const [payments, setPayments] = useState([]);
  const [members, setMembers] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [membershipPricing, setMembershipPricing] = useState({});
  const [formData, setFormData] = useState({
    member_id: "",
    payment_method: "cash",
    membership_type: "basic",
    notes: "",
  });

  useEffect(() => {
    fetchPayments();
    fetchMembers();
    fetchMembershipPricing();
  }, []);

  const fetchPayments = async () => {
    try {
      const response = await api.get(`/payments`);
      setPayments(response.data);
    } catch (error) {
      console.error("Error fetching payments:", error);
    }
  };

  const fetchMembers = async () => {
    try {
      const response = await api.get(`/members`);
      setMembers(response.data);
    } catch (error) {
      console.error("Error fetching members:", error);
    }
  };

  const fetchMembershipPricing = async () => {
    try {
      const response = await api.get(`/membership-pricing`);
      setMembershipPricing(response.data);
    } catch (error) {
      console.error("Error fetching pricing:", error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const paymentData = { ...formData, amount: membershipPricing[formData.membership_type] };
      await api.post(`/payments`, paymentData);
      setFormData({ member_id: "", payment_method: "cash", membership_type: "basic", notes: "" });
      setShowAddForm(false);
      fetchPayments();
    } catch (error) {
      console.error("Error creating payment:", error);
      alert("Error creating payment. Please try again.");
    }
  };

  const getMemberName = (memberId) => {
    const member = members.find((m) => m.id === memberId);
    return member ? `${member.first_name} ${member.last_name}` : "Unknown";
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <h2 className="text-2xl font-bold text-gray-900">Payment Management</h2>
        <button onClick={() => setShowAddForm(true)} className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors">
          Record Cash Payment
        </button>
      </div>

      <div className="bg-blue-50 p-4 rounded-lg">
        <h3 className="font-semibold text-blue-900 mb-2">💡 Payment Processing</h3>
        <div className="text-blue-800 text-sm space-y-1">
          <p>
            <strong>Automatic Payments:</strong> Credit card payments are processed automatically via Stripe/Razorpay when
            members are added with auto-billing.
          </p>
          <p>
            <strong>Manual Payments:</strong> Use "Record Cash Payment" for cash, check, or bank transfer payments.
          </p>
        </div>
      </div>

      {showAddForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-40 p-4">
          <div className="bg-white p-6 lg:p-8 rounded-lg max-w-md w-full">
            <h3 className="text-xl font-bold mb-6">Record Cash Payment</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Member</label>
                <select
                  value={formData.member_id}
                  onChange={(e) => setFormData({ ...formData, member_id: e.target.value })}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                >
                  <option value="">Select Member</option>
                  {members.map((member) => (
                    <option key={member.id} value={member.id}>
                      {member.first_name} {member.last_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Membership Type</label>
                <select
                  value={formData.membership_type}
                  onChange={(e) => setFormData({ ...formData, membership_type: e.target.value })}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="basic">Basic - ${membershipPricing.basic}</option>
                  <option value="premium">Premium - ${membershipPricing.premium}</option>
                  <option value="vip">VIP - ${membershipPricing.vip}</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Payment Method</label>
                <select
                  value={formData.payment_method}
                  onChange={(e) => setFormData({ ...formData, payment_method: e.target.value })}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="cash">Cash</option>
                  <option value="check">Check</option>
                  <option value="bank_transfer">Bank Transfer</option>
                </select>
              </div>
              <textarea
                placeholder="Notes (Optional)"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="w-full p-3 border rounded-lg h-20 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <div className="flex flex-col sm:flex-row gap-4">
                <button type="submit" className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors">
                  Record Payment
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddForm(false);
                    setFormData({ member_id: "", payment_method: "cash", membership_type: "basic", notes: "" });
                  }}
                  className="bg-gray-500 text-white px-6 py-2 rounded-lg hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Member</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden sm:table-cell">Method</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden lg:table-cell">Membership</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {payments.map((payment) => (
                <tr key={payment.id}>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    <div className="truncate max-w-32">{getMemberName(payment.member_id)}</div>
                  </td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm text-gray-500">${payment.amount}</td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden sm:table-cell">
                    {payment.payment_method.replace("_", " ").toUpperCase()}
                  </td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap hidden lg:table-cell">
                    <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                      {payment.membership_type.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(payment.payment_date).toLocaleDateString()}
                  </td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                      {payment.status.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

/** =========================
 *  Dashboard
 *  ========================= */
const Dashboard = ({ onNavigate }) => {
  const [stats, setStats] = useState({
    total_members: 0,
    active_members: 0,
    monthly_revenue: 0,
    pending_payments: 0,
    todays_checkins: 0,
  });
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    fetchDashboardStats();
    fetchProfile();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const response = await api.get(`/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error("Error fetching dashboard stats:", error);
    }
  };

  const fetchProfile = async () => {
    try {
      const response = await api.get(`/profile`);
      setProfile(response.data);
    } catch (error) {
      console.error("Error fetching profile:", error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="relative bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg overflow-hidden">
        <div className="absolute inset-0 bg-black opacity-20"></div>
        <div
          className="relative bg-cover bg-center h-48 lg:h-64 flex items-center justify-center"
          style={{
            backgroundImage: `url('https://images.unsplash.com/photo-1534438327276-14e5300c3a48?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHxneW18ZW58MHx8fHwxNzUyNDU1NzU1fDA&ixlib=rb-4.1.0&q=85')`,
          }}
        >
          <div className="text-center text-white z-10 p-4">
            <h1 className="text-3xl lg:text-4xl font-bold mb-2 lg:mb-4">{profile?.gym_name || "FitForce"} Dashboard</h1>
            <p className="text-lg lg:text-xl">Professional Gym Management System</p>
          </div>
        </div>
      </div>

      {/* cards ... unchanged */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 lg:gap-6">
        {/* Total Members */}
        <div className="bg-white p-4 lg:p-6 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-blue-100 text-blue-600">
              <svg className="w-5 h-5 lg:w-6 lg:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-xs lg:text-sm font-medium text-gray-600">Total Members</p>
              <p className="text-xl lg:text-2xl font-semibold text-gray-900">{stats.total_members}</p>
            </div>
          </div>
        </div>

        {/* Active Members */}
        <div className="bg-white p-4 lg:p-6 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-green-100 text-green-600">
              <svg className="w-5 h-5 lg:w-6 lg:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-xs lg:text-sm font-medium text-gray-600">Active Members</p>
              <p className="text-xl lg:text-2xl font-semibold text-gray-900">{stats.active_members}</p>
            </div>
          </div>
        </div>

        {/* Monthly Revenue */}
        <div className="bg-white p-4 lg:p-6 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-yellow-100 text-yellow-600">
              <svg className="w-5 h-5 lg:w-6 lg:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-xs lg:text-sm font-medium text-gray-600">Monthly Revenue</p>
              <p className="text-xl lg:text-2xl font-semibold text-gray-900">${stats.monthly_revenue.toFixed(2)}</p>
            </div>
          </div>
        </div>

        {/* Expired */}
        <div className="bg-white p-4 lg:p-6 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-red-100 text-red-600">
              <svg className="w-5 h-5 lg:w-6 lg:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.664-.833-2.464 0L4.35 15.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-xs lg:text-sm font-medium text-gray-600">Expired</p>
              <p className="text-xl lg:text-2xl font-semibold text-gray-900">{stats.pending_payments}</p>
            </div>
          </div>
        </div>

        {/* Today's Check-ins */}
        <div className="bg-white p-4 lg:p-6 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-purple-100 text-purple-600">
              <svg className="w-5 h-5 lg:w-6 lg:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-xs lg:text-sm font-medium text-gray-600">Today's Check-ins</p>
              <p className="text-xl lg:text-2xl font-semibold text-gray-900">{stats.todays_checkins}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick actions + plans (unchanged) */}
      {/* ... (kept your content exactly) ... */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Quick Actions */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <button onClick={() => onNavigate("members")} className="w-full text-left p-4 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors">
              <div className="font-medium text-blue-900">Manage Members</div>
              <div className="text-sm text-blue-600">Add, edit, or view member information</div>
            </button>
            <button onClick={() => onNavigate("payments")} className="w-full text-left p-4 bg-green-50 hover:bg-green-100 rounded-lg transition-colors">
              <div className="font-medium text-green-900">Record Payment</div>
              <div className="text-sm text-green-600">Process member payments and renewals</div>
            </button>
            <button onClick={() => onNavigate("attendance")} className="w-full text-left p-4 bg-purple-50 hover:bg-purple-100 rounded-lg transition-colors">
              <div className="font-medium text-purple-900">Check-in Member</div>
              <div className="text-sm text-purple-600">Track member attendance</div>
            </button>
          </div>
        </div>

        {/* Membership Plans */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Membership Plans</h3>
          {/* your original three plan cards */}
          <div className="space-y-4">
            <div className="border border-blue-200 rounded-lg p-4 bg-blue-50">
              <div className="flex justify-between items-center">
                <div>
                  <h4 className="font-semibold text-blue-900">Basic</h4>
                  <p className="text-sm text-blue-600">Access to gym equipment</p>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-blue-900">$29.99</div>
                  <div className="text-sm text-blue-600">per month</div>
                </div>
              </div>
            </div>
            <div className="border border-purple-200 rounded-lg p-4 bg-purple-50">
              <div className="flex justify-between items-center">
                <div>
                  <h4 className="font-semibold text-purple-900">Premium</h4>
                  <p className="text-sm text-purple-600">Gym + Classes + Locker</p>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-purple-900">$49.99</div>
                  <div className="text-sm text-purple-600">per month</div>
                </div>
              </div>
            </div>
            <div className="border border-yellow-400 rounded-lg p-4 bg-gradient-to-r from-yellow-50 to-orange-50">
              <div className="flex justify-between items-center">
                <div>
                  <h4 className="font-semibold text-yellow-800">VIP</h4>
                  <p className="text-sm text-yellow-700">All Access + Personal Training</p>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-yellow-800">$79.99</div>
                  <div className="text-sm text-yellow-700">per month</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>      
    </div>
  );
};

/** =========================
 *  Attendance
 *  ========================= */
const AttendanceManagement = ({ onNavigate }) => {
  const [attendance, setAttendance] = useState([]);
  const [members, setMembers] = useState([]);
  const [showCheckinForm, setShowCheckinForm] = useState(false);
  const [selectedMember, setSelectedMember] = useState("");

  useEffect(() => {
    fetchAttendance();
    fetchMembers();
  }, []);

  const fetchAttendance = async () => {
    try {
      const response = await api.get(`/attendance`);
      setAttendance(response.data);
    } catch (error) {
      console.error("Error fetching attendance:", error);
    }
  };

  const fetchMembers = async () => {
    try {
      const response = await api.get(`/members`);
      setMembers(response.data.filter((member) => member.status === "active"));
    } catch (error) {
      console.error("Error fetching members:", error);
    }
  };

  const handleCheckin = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/attendance/checkin`, { member_id: selectedMember });
      setSelectedMember("");
      setShowCheckinForm(false);
      fetchAttendance();
      alert("Member checked in successfully!");
    } catch (error) {
      console.error("Error checking in member:", error);
      alert("Error checking in member. They may already be checked in today.");
    }
  };

  const handleCheckout = async (memberId) => {
    try {
      await api.post(`/attendance/checkout/${memberId}`);
      fetchAttendance();
      alert("Member checked out successfully!");
    } catch (error) {
      console.error("Error checking out member:", error);
      alert("Error checking out member.");
    }
  };

  const getMemberName = (memberId) => {
    const member = members.find((m) => m.id === memberId);
    return member ? `${member.first_name} ${member.last_name}` : "Unknown";
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <h2 className="text-2xl font-bold text-gray-900">Attendance Management</h2>
        <button onClick={() => setShowCheckinForm(true)} className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700 transition-colors">
          Check-in Member
        </button>
      </div>

      {showCheckinForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-40 p-4">
          <div className="bg-white p-6 lg:p-8 rounded-lg max-w-md w-full">
            <h3 className="text-xl font-bold mb-6">Check-in Member</h3>
            <form onSubmit={handleCheckin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Select Member</label>
                <select
                  value={selectedMember}
                  onChange={(e) => setSelectedMember(e.target.value)}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                >
                  <option value="">Select Member</option>
                  {members.map((member) => (
                    <option key={member.id} value={member.id}>
                      {member.first_name} {member.last_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col sm:flex-row gap-4">
                <button type="submit" className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700 transition-colors">
                  Check In
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowCheckinForm(false);
                    setSelectedMember("");
                  }}
                  className="bg-gray-500 text-white px-6 py-2 rounded-lg hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Member</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Check-in</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden sm:table-cell">Check-out</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden lg:table-cell">Date</th>
                <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {attendance.map((record) => (
                <tr key={record.id}>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    <div className="truncate max-w-32">{getMemberName(record.member_id)}</div>
                  </td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(record.check_in_time).toLocaleTimeString()}</td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden sm:table-cell">
                    {record.check_out_time ? new Date(record.check_out_time).toLocaleTimeString() : "Still active"}
                  </td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden lg:table-cell">
                    {new Date(record.date).toLocaleDateString()}
                  </td>
                  <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm">
                    {!record.check_out_time && (
                      <button onClick={() => handleCheckout(record.member_id)} className="text-red-600 hover:text-red-900">
                        Check Out
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

/** =========================
 *  Main App (adds auth guard)
 *  ========================= */
function App() {
  const [currentView, setCurrentView] = useState("dashboard");
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [token, setToken] = useState(getToken());

  const navigation = [
    { id: "dashboard", name: "Dashboard", icon: "🏠" },
    { id: "members", name: "Members", icon: "👥" },
    { id: "payments", name: "Payments", icon: "💳" },
    { id: "attendance", name: "Attendance", icon: "📋" },
  ];

  const handleLoginSuccess = (tok) => {
    setToken(tok);
  };

  const handleLogout = () => {
    clearToken();
    setToken(null);
    setCurrentView("dashboard");
  };

  const renderContent = () => {
    switch (currentView) {
      case "dashboard":
        return <Dashboard onNavigate={setCurrentView} />;
      case "members":
        return <MemberManagement onNavigate={setCurrentView} />;
      case "payments":
        return <PaymentManagement onNavigate={setCurrentView} />;
      case "attendance":
        return <AttendanceManagement onNavigate={setCurrentView} />;
      case "profile":
        return <ProfileManagement onNavigate={setCurrentView} />;
      default:
        return <Dashboard onNavigate={setCurrentView} />;
    }
  };

  // Not logged in → show login
  if (!token) {
    return <Login onSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="min-h-screen bg-gray-100 flex">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && <div className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)}></div>}

      {/* Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out
        lg:relative lg:translate-x-0 lg:flex lg:flex-col
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">FitForce</h1>
              <p className="text-sm text-gray-600">Professional Gym Management</p>
            </div>
            <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-gray-500 hover:text-gray-700">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        <nav className="flex-1 mt-6 overflow-y-auto">
          {navigation.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                setCurrentView(item.id);
                setSidebarOpen(false);
              }}
              className={`w-full text-left px-6 py-3 flex items-center space-x-3 hover:bg-gray-50 transition-colors ${
                currentView === item.id ? "bg-blue-50 border-r-4 border-blue-600 text-blue-600" : "text-gray-700"
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="font-medium">{item.name}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white shadow-sm border-b border-gray-200 px-4 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center">
              <button onClick={() => setSidebarOpen(true)} className="lg:hidden mr-4 text-gray-500 hover:text-gray-700">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <h2 className="text-xl font-semibold text-gray-900 capitalize">{currentView}</h2>
            </div>
            <div className="relative">
              <button onClick={() => setShowProfileDropdown(!showProfileDropdown)} className="flex items-center space-x-2 text-gray-700 hover:text-gray-900 focus:outline-none">
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <span className="text-white font-medium text-sm">👤</span>
                </div>
                <span className="font-medium hidden sm:block">Profile</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {showProfileDropdown && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-50">
                  <div className="py-1">
                    <button
                      onClick={() => {
                        setCurrentView("profile");
                        setShowProfileDropdown(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      Manage Profile
                    </button>
                    <button
                      onClick={() => {
                        handleLogout();
                        setShowProfileDropdown(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                    >
                      Log out
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 p-4 lg:p-8 overflow-auto">{renderContent()}</main>
      </div>
    </div>
  );
}

export default App;
