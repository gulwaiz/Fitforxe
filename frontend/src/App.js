import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Profile Management Component
const ProfileManagement = ({ onNavigate }) => {
  const [profile, setProfile] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    gym_name: 'FitForce',
    owner_name: '',
    email: '',
    phone: '',
    address: '',
    city: '',
    state: '',
    zip_code: ''
  });

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${API}/profile`);
      setProfile(response.data);
      setFormData({
        gym_name: response.data.gym_name || 'FitForce',
        owner_name: response.data.owner_name || '',
        email: response.data.email || '',
        phone: response.data.phone || '',
        address: response.data.address || '',
        city: response.data.city || '',
        state: response.data.state || '',
        zip_code: response.data.zip_code || ''
      });
    } catch (error) {
      console.error('Error fetching profile:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (profile && profile.id) {
        await axios.put(`${API}/profile`, formData);
      } else {
        await axios.post(`${API}/profile`, formData);
      }
      setIsEditing(false);
      fetchProfile();
      alert('Profile updated successfully!');
    } catch (error) {
      console.error('Error updating profile:', error);
      alert('Error updating profile. Please try again.');
    }
  };

  if (!profile) {
    return <div>Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Gym Owner Profile</h2>
        <button
          onClick={() => setIsEditing(!isEditing)}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          {isEditing ? 'Cancel' : 'Edit Profile'}
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-md p-8">
        {isEditing ? (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Gym Name
                </label>
                <input
                  type="text"
                  value={formData.gym_name}
                  onChange={(e) => setFormData({...formData, gym_name: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Owner Name
                </label>
                <input
                  type="text"
                  value={formData.owner_name}
                  onChange={(e) => setFormData({...formData, owner_name: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Phone
                </label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({...formData, phone: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                  required
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Address
                </label>
                <input
                  type="text"
                  value={formData.address}
                  onChange={(e) => setFormData({...formData, address: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  City
                </label>
                <input
                  type="text"
                  value={formData.city}
                  onChange={(e) => setFormData({...formData, city: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  State
                </label>
                <input
                  type="text"
                  value={formData.state}
                  onChange={(e) => setFormData({...formData, state: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Zip Code
                </label>
                <input
                  type="text"
                  value={formData.zip_code}
                  onChange={(e) => setFormData({...formData, zip_code: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                  required
                />
              </div>
            </div>
            <div className="flex space-x-4">
              <button
                type="submit"
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
              >
                Save Changes
              </button>
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="bg-gray-500 text-white px-6 py-2 rounded-lg hover:bg-gray-600"
              >
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
                  <p><span className="font-medium">Gym Name:</span> {profile.gym_name}</p>
                  <p><span className="font-medium">Owner:</span> {profile.owner_name}</p>
                  <p><span className="font-medium">Email:</span> {profile.email}</p>
                  <p><span className="font-medium">Phone:</span> {profile.phone}</p>
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Address</h3>
                <div className="space-y-2">
                  <p>{profile.address}</p>
                  <p>{profile.city}, {profile.state} {profile.zip_code}</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Member Management Component with Stripe Integration
const MemberManagement = ({ onNavigate }) => {
  const [members, setMembers] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingMember, setEditingMember] = useState(null);
  const [membershipPricing, setMembershipPricing] = useState({});
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    membership_type: 'basic',
    emergency_contact_name: '',
    emergency_contact_phone: '',
    medical_conditions: '',
    enable_auto_billing: false,
    // Credit card fields
    card_holder_name: '',
    card_number: '',
    expiry_date: '',
    cvv: ''
  });

  // Credit card formatting functions
  const formatCardNumber = (value) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    const matches = v.match(/\d{4,16}/g);
    const match = matches && matches[0] || '';
    const parts = [];
    for (let i = 0, len = match.length; i < len; i += 4) {
      parts.push(match.substring(i, i + 4));
    }
    if (parts.length) {
      return parts.join(' ');
    } else {
      return v;
    }
  };

  const formatExpiryDate = (value) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    if (v.length >= 2) {
      return v.substring(0, 2) + '/' + v.substring(2, 4);
    }
    return v;
  };

  const handleCardInputChange = (field, value) => {
    let formattedValue = value;
    if (field === 'card_number') {
      formattedValue = formatCardNumber(value);
    } else if (field === 'expiry_date') {
      formattedValue = formatExpiryDate(value);
    } else if (field === 'cvv') {
      formattedValue = value.replace(/[^0-9]/g, '');
    }
    setFormData({...formData, [field]: formattedValue});
  };

  useEffect(() => {
    fetchMembers();
    fetchMembershipPricing();
  }, []);

  const fetchMembers = async () => {
    try {
      const response = await axios.get(`${API}/members`);
      setMembers(response.data);
    } catch (error) {
      console.error('Error fetching members:', error);
    }
  };

  const fetchMembershipPricing = async () => {
    try {
      const response = await axios.get(`${API}/membership-pricing`);
      setMembershipPricing(response.data);
    } catch (error) {
      console.error('Error fetching pricing:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingMember) {
        await axios.put(`${API}/members/${editingMember.id}`, formData);
      } else {
        // Create member first
        const memberResponse = await axios.post(`${API}/members`, formData);
        const newMember = memberResponse.data;
        
        // If auto billing is enabled, redirect to Stripe checkout
        if (formData.enable_auto_billing) {
          const currentUrl = window.location.origin + window.location.pathname;
          const stripeRequest = {
            member_id: newMember.id,
            membership_type: formData.membership_type,
            success_url: `${currentUrl}?payment_success=true&session_id={CHECKOUT_SESSION_ID}`,
            cancel_url: `${currentUrl}?payment_cancelled=true`
          };
          
          const stripeResponse = await axios.post(`${API}/stripe/checkout`, stripeRequest);
          window.location.href = stripeResponse.data.url;
          return;
        }
      }
      
      setFormData({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        membership_type: 'basic',
        emergency_contact_name: '',
        emergency_contact_phone: '',
        medical_conditions: '',
        enable_auto_billing: false,
        card_holder_name: '',
        card_number: '',
        expiry_date: '',
        cvv: ''
      });
      setShowAddForm(false);
      setEditingMember(null);
      fetchMembers();
    } catch (error) {
      console.error('Error saving member:', error);
      alert('Error saving member. Please try again.');
    }
  };

  const handleEdit = (member) => {
    setEditingMember(member);
    setFormData({
      first_name: member.first_name,
      last_name: member.last_name,
      email: member.email,
      phone: member.phone,
      membership_type: member.membership_type,
      emergency_contact_name: member.emergency_contact_name || '',
      emergency_contact_phone: member.emergency_contact_phone || '',
      medical_conditions: member.medical_conditions || '',
      enable_auto_billing: member.auto_billing_enabled || false,
      card_holder_name: '',
      card_number: '',
      expiry_date: '',
      cvv: ''
    });
    setShowAddForm(true);
  };

  const handleDelete = async (memberId) => {
    if (window.confirm('Are you sure you want to delete this member?')) {
      try {
        await axios.delete(`${API}/members/${memberId}`);
        fetchMembers();
      } catch (error) {
        console.error('Error deleting member:', error);
      }
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'inactive': return 'bg-gray-100 text-gray-800';
      case 'expired': return 'bg-red-100 text-red-800';
      case 'suspended': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getMembershipColor = (type) => {
    switch (type) {
      case 'basic': return 'bg-blue-100 text-blue-800';
      case 'premium': return 'bg-purple-100 text-purple-800';
      case 'vip': return 'bg-gold-100 text-gold-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Member Management</h2>
        <button
          onClick={() => setShowAddForm(true)}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          Add New Member
        </button>
      </div>

      {showAddForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg max-w-2xl w-full mx-4 max-h-screen overflow-y-auto">
            <h3 className="text-xl font-bold mb-6">
              {editingMember ? 'Edit Member' : 'Add New Member'}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="First Name"
                  value={formData.first_name}
                  onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                  className="p-3 border rounded-lg"
                  required
                />
                <input
                  type="text"
                  placeholder="Last Name"
                  value={formData.last_name}
                  onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                  className="p-3 border rounded-lg"
                  required
                />
              </div>
              <input
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="w-full p-3 border rounded-lg"
                required
              />
              <input
                type="tel"
                placeholder="Phone"
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
                className="w-full p-3 border rounded-lg"
                required
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Membership Type
                </label>
                <select
                  value={formData.membership_type}
                  onChange={(e) => setFormData({...formData, membership_type: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                >
                  <option value="basic">Basic - ${membershipPricing.basic}/month</option>
                  <option value="premium">Premium - ${membershipPricing.premium}/month</option>
                  <option value="vip">VIP - ${membershipPricing.vip}/month</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Emergency Contact Name"
                  value={formData.emergency_contact_name}
                  onChange={(e) => setFormData({...formData, emergency_contact_name: e.target.value})}
                  className="p-3 border rounded-lg"
                />
                <input
                  type="tel"
                  placeholder="Emergency Contact Phone"
                  value={formData.emergency_contact_phone}
                  onChange={(e) => setFormData({...formData, emergency_contact_phone: e.target.value})}
                  className="p-3 border rounded-lg"
                />
              </div>
              <textarea
                placeholder="Medical Conditions (Optional)"
                value={formData.medical_conditions}
                onChange={(e) => setFormData({...formData, medical_conditions: e.target.value})}
                className="w-full p-3 border rounded-lg h-24"
              />
              {!editingMember && (
                <div className="bg-blue-50 p-4 rounded-lg">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.enable_auto_billing}
                      onChange={(e) => setFormData({...formData, enable_auto_billing: e.target.checked})}
                      className="mr-3"
                    />
                    <span className="text-sm">
                      <strong>Enable Auto-Billing</strong> - Set up automatic monthly payments via credit card
                    </span>
                  </label>
                  {formData.enable_auto_billing && (
                    <div className="mt-4 p-4 bg-white rounded-lg border">
                      <h4 className="font-semibold text-gray-900 mb-3">💳 Credit Card Information</h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="col-span-2">
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Cardholder Name
                          </label>
                          <input
                            type="text"
                            placeholder="John Doe"
                            value={formData.card_holder_name}
                            onChange={(e) => setFormData({...formData, card_holder_name: e.target.value})}
                            className="w-full p-3 border rounded-lg"
                            required={formData.enable_auto_billing}
                          />
                        </div>
                        <div className="col-span-2">
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Card Number
                          </label>
                          <input
                            type="text"
                            placeholder="1234 5678 9012 3456"
                            value={formData.card_number}
                            onChange={(e) => handleCardInputChange('card_number', e.target.value)}
                            maxLength="19"
                            className="w-full p-3 border rounded-lg"
                            required={formData.enable_auto_billing}
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Expiry Date
                          </label>
                          <input
                            type="text"
                            placeholder="MM/YY"
                            value={formData.expiry_date}
                            onChange={(e) => handleCardInputChange('expiry_date', e.target.value)}
                            maxLength="5"
                            className="w-full p-3 border rounded-lg"
                            required={formData.enable_auto_billing}
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            CVV
                          </label>
                          <input
                            type="text"
                            placeholder="123"
                            value={formData.cvv}
                            onChange={(e) => handleCardInputChange('cvv', e.target.value)}
                            maxLength="4"
                            className="w-full p-3 border rounded-lg"
                            required={formData.enable_auto_billing}
                          />
                        </div>
                      </div>
                      <div className="mt-4 p-3 bg-green-50 rounded-lg">
                        <div className="flex items-center">
                          <svg className="w-5 h-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.707-4.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L9 10.586l7.293-7.293a1 1 0 011.414 0z" />
                          </svg>
                          <span className="text-sm text-green-800">
                            <strong>Secure Payment:</strong> All credit card information is processed securely via Stripe encryption
                          </span>
                        </div>
                      </div>
                      <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                        <p className="text-sm text-blue-800">
                          <strong>Auto-Billing Setup:</strong> Monthly membership fee (${membershipPricing[formData.membership_type] || '0'}) 
                          will be automatically charged to this card each month.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
              <div className="flex space-x-4">
                <button
                  type="submit"
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
                >
                  {editingMember ? 'Update Member' : 'Add Member'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddForm(false);
                    setEditingMember(null);
                    setFormData({
                      first_name: '',
                      last_name: '',
                      email: '',
                      phone: '',
                      membership_type: 'basic',
                      emergency_contact_name: '',
                      emergency_contact_phone: '',
                      medical_conditions: '',
                      enable_auto_billing: false,
                      card_holder_name: '',
                      card_number: '',
                      expiry_date: '',
                      cvv: ''
                    });
                  }}
                  className="bg-gray-500 text-white px-6 py-2 rounded-lg hover:bg-gray-600"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Phone</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Membership</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Auto-Billing</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {members.map((member) => (
              <tr key={member.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">
                    {member.first_name} {member.last_name}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {member.email}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {member.phone}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getMembershipColor(member.membership_type)}`}>
                    {member.membership_type.toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(member.status)}`}>
                    {member.status.toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {member.auto_billing_enabled ? (
                    <span className="text-green-600">✓ Enabled</span>
                  ) : (
                    <span className="text-gray-400">Disabled</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                  <button
                    onClick={() => handleEdit(member)}
                    className="text-blue-600 hover:text-blue-900"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(member.id)}
                    className="text-red-600 hover:text-red-900"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Payment Management Component
const PaymentManagement = ({ onNavigate }) => {
  const [payments, setPayments] = useState([]);
  const [members, setMembers] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [membershipPricing, setMembershipPricing] = useState({});
  const [formData, setFormData] = useState({
    member_id: '',
    payment_method: 'cash',
    membership_type: 'basic',
    notes: ''
  });

  useEffect(() => {
    fetchPayments();
    fetchMembers();
    fetchMembershipPricing();
  }, []);

  const fetchPayments = async () => {
    try {
      const response = await axios.get(`${API}/payments`);
      setPayments(response.data);
    } catch (error) {
      console.error('Error fetching payments:', error);
    }
  };

  const fetchMembers = async () => {
    try {
      const response = await axios.get(`${API}/members`);
      setMembers(response.data);
    } catch (error) {
      console.error('Error fetching members:', error);
    }
  };

  const fetchMembershipPricing = async () => {
    try {
      const response = await axios.get(`${API}/membership-pricing`);
      setMembershipPricing(response.data);
    } catch (error) {
      console.error('Error fetching pricing:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const paymentData = {
        ...formData,
        amount: membershipPricing[formData.membership_type]
      };
      await axios.post(`${API}/payments`, paymentData);
      setFormData({
        member_id: '',
        payment_method: 'cash',
        membership_type: 'basic',
        notes: ''
      });
      setShowAddForm(false);
      fetchPayments();
    } catch (error) {
      console.error('Error creating payment:', error);
      alert('Error creating payment. Please try again.');
    }
  };

  const getMemberName = (memberId) => {
    const member = members.find(m => m.id === memberId);
    return member ? `${member.first_name} ${member.last_name}` : 'Unknown';
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Payment Management</h2>
        <button
          onClick={() => setShowAddForm(true)}
          className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors"
        >
          Record Cash Payment
        </button>
      </div>

      <div className="bg-blue-50 p-4 rounded-lg">
        <h3 className="font-semibold text-blue-900 mb-2">💡 Payment Processing</h3>
        <p className="text-blue-800 text-sm">
          <strong>Automatic Payments:</strong> Credit card payments are processed automatically via Stripe when members are added with auto-billing enabled.
          <br />
          <strong>Manual Payments:</strong> Use the "Record Cash Payment" button for cash, check, or bank transfer payments.
        </p>
      </div>

      {showAddForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg max-w-md w-full mx-4">
            <h3 className="text-xl font-bold mb-6">Record Cash Payment</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Member
                </label>
                <select
                  value={formData.member_id}
                  onChange={(e) => setFormData({...formData, member_id: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                  required
                >
                  <option value="">Select Member</option>
                  {members.map(member => (
                    <option key={member.id} value={member.id}>
                      {member.first_name} {member.last_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Membership Type
                </label>
                <select
                  value={formData.membership_type}
                  onChange={(e) => setFormData({...formData, membership_type: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                >
                  <option value="basic">Basic - ${membershipPricing.basic}</option>
                  <option value="premium">Premium - ${membershipPricing.premium}</option>
                  <option value="vip">VIP - ${membershipPricing.vip}</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Payment Method
                </label>
                <select
                  value={formData.payment_method}
                  onChange={(e) => setFormData({...formData, payment_method: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                >
                  <option value="cash">Cash</option>
                  <option value="check">Check</option>
                  <option value="bank_transfer">Bank Transfer</option>
                </select>
              </div>
              <textarea
                placeholder="Notes (Optional)"
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                className="w-full p-3 border rounded-lg h-20"
              />
              <div className="flex space-x-4">
                <button
                  type="submit"
                  className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700"
                >
                  Record Payment
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddForm(false);
                    setFormData({
                      member_id: '',
                      payment_method: 'cash',
                      membership_type: 'basic',
                      notes: ''
                    });
                  }}
                  className="bg-gray-500 text-white px-6 py-2 rounded-lg hover:bg-gray-600"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Member</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Payment Method</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Membership</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {payments.map((payment) => (
              <tr key={payment.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {getMemberName(payment.member_id)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  ${payment.amount}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {payment.payment_method.replace('_', ' ').toUpperCase()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                    {payment.membership_type.toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(payment.payment_date).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
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
  );
};

// Dashboard Component
const Dashboard = ({ onNavigate }) => {
  const [stats, setStats] = useState({
    total_members: 0,
    active_members: 0,
    monthly_revenue: 0,
    pending_payments: 0,
    todays_checkins: 0
  });
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    fetchDashboardStats();
    fetchProfile();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
    }
  };

  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${API}/profile`);
      setProfile(response.data);
    } catch (error) {
      console.error('Error fetching profile:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="relative bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg overflow-hidden">
        <div className="absolute inset-0 bg-black opacity-20"></div>
        <div 
          className="relative bg-cover bg-center h-64 flex items-center justify-center"
          style={{
            backgroundImage: `url('https://images.unsplash.com/photo-1534438327276-14e5300c3a48?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHxneW18ZW58MHx8fHwxNzUyNDU1NzU1fDA&ixlib=rb-4.1.0&q=85')`
          }}
        >
          <div className="text-center text-white z-10">
            <h1 className="text-4xl font-bold mb-4">{profile?.gym_name || 'FitForce'} Dashboard</h1>
            <p className="text-xl">Professional Gym Management System</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-blue-100 text-blue-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Members</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.total_members}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-green-100 text-green-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Active Members</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.active_members}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-yellow-100 text-yellow-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Monthly Revenue</p>
              <p className="text-2xl font-semibold text-gray-900">${stats.monthly_revenue.toFixed(2)}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-red-100 text-red-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.664-.833-2.464 0L4.35 15.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Expired Memberships</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.pending_payments}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-purple-100 text-purple-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Today's Check-ins</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.todays_checkins}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <button
              onClick={() => onNavigate('members')}
              className="w-full text-left p-4 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
            >
              <div className="font-medium text-blue-900">Manage Members</div>
              <div className="text-sm text-blue-600">Add, edit, or view member information</div>
            </button>
            <button
              onClick={() => onNavigate('payments')}
              className="w-full text-left p-4 bg-green-50 hover:bg-green-100 rounded-lg transition-colors"
            >
              <div className="font-medium text-green-900">Record Payment</div>
              <div className="text-sm text-green-600">Process member payments and renewals</div>
            </button>
            <button
              onClick={() => onNavigate('attendance')}
              className="w-full text-left p-4 bg-purple-50 hover:bg-purple-100 rounded-lg transition-colors"
            >
              <div className="font-medium text-purple-900">Check-in Member</div>
              <div className="text-sm text-purple-600">Track member attendance</div>
            </button>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Membership Plans</h3>
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

// Attendance Component
const AttendanceManagement = ({ onNavigate }) => {
  const [attendance, setAttendance] = useState([]);
  const [members, setMembers] = useState([]);
  const [showCheckinForm, setShowCheckinForm] = useState(false);
  const [selectedMember, setSelectedMember] = useState('');

  useEffect(() => {
    fetchAttendance();
    fetchMembers();
  }, []);

  const fetchAttendance = async () => {
    try {
      const response = await axios.get(`${API}/attendance`);
      setAttendance(response.data);
    } catch (error) {
      console.error('Error fetching attendance:', error);
    }
  };

  const fetchMembers = async () => {
    try {
      const response = await axios.get(`${API}/members`);
      setMembers(response.data.filter(member => member.status === 'active'));
    } catch (error) {
      console.error('Error fetching members:', error);
    }
  };

  const handleCheckin = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/attendance/checkin`, {
        member_id: selectedMember
      });
      setSelectedMember('');
      setShowCheckinForm(false);
      fetchAttendance();
      alert('Member checked in successfully!');
    } catch (error) {
      console.error('Error checking in member:', error);
      alert('Error checking in member. They may already be checked in today.');
    }
  };

  const handleCheckout = async (memberId) => {
    try {
      await axios.post(`${API}/attendance/checkout/${memberId}`);
      fetchAttendance();
      alert('Member checked out successfully!');
    } catch (error) {
      console.error('Error checking out member:', error);
      alert('Error checking out member.');
    }
  };

  const getMemberName = (memberId) => {
    const member = members.find(m => m.id === memberId);
    return member ? `${member.first_name} ${member.last_name}` : 'Unknown';
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Attendance Management</h2>
        <button
          onClick={() => setShowCheckinForm(true)}
          className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700 transition-colors"
        >
          Check-in Member
        </button>
      </div>

      {showCheckinForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg max-w-md w-full mx-4">
            <h3 className="text-xl font-bold mb-6">Check-in Member</h3>
            <form onSubmit={handleCheckin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Member
                </label>
                <select
                  value={selectedMember}
                  onChange={(e) => setSelectedMember(e.target.value)}
                  className="w-full p-3 border rounded-lg"
                  required
                >
                  <option value="">Select Member</option>
                  {members.map(member => (
                    <option key={member.id} value={member.id}>
                      {member.first_name} {member.last_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex space-x-4">
                <button
                  type="submit"
                  className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700"
                >
                  Check In
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowCheckinForm(false);
                    setSelectedMember('');
                  }}
                  className="bg-gray-500 text-white px-6 py-2 rounded-lg hover:bg-gray-600"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Member</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Check-in Time</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Check-out Time</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {attendance.map((record) => (
              <tr key={record.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {getMemberName(record.member_id)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(record.check_in_time).toLocaleTimeString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {record.check_out_time ? new Date(record.check_out_time).toLocaleTimeString() : 'Still active'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(record.date).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {!record.check_out_time && (
                    <button
                      onClick={() => handleCheckout(record.member_id)}
                      className="text-red-600 hover:text-red-900"
                    >
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
  );
};

// Main App Component
function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);

  const navigation = [
    { id: 'dashboard', name: 'Dashboard', icon: '🏠' },
    { id: 'members', name: 'Members', icon: '👥' },
    { id: 'payments', name: 'Payments', icon: '💳' },
    { id: 'attendance', name: 'Attendance', icon: '📋' }
  ];

  const renderContent = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard onNavigate={setCurrentView} />;
      case 'members':
        return <MemberManagement onNavigate={setCurrentView} />;
      case 'payments':
        return <PaymentManagement onNavigate={setCurrentView} />;
      case 'attendance':
        return <AttendanceManagement onNavigate={setCurrentView} />;
      case 'profile':
        return <ProfileManagement onNavigate={setCurrentView} />;
      default:
        return <Dashboard onNavigate={setCurrentView} />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="flex">
        {/* Sidebar */}
        <div className="w-64 bg-white shadow-lg">
          <div className="p-6">
            <h1 className="text-2xl font-bold text-gray-900">FitForce</h1>
            <p className="text-sm text-gray-600">Professional Gym Management</p>
          </div>
          <nav className="mt-6">
            {navigation.map((item) => (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id)}
                className={`w-full text-left px-6 py-3 flex items-center space-x-3 hover:bg-gray-50 transition-colors ${
                  currentView === item.id ? 'bg-blue-50 border-r-4 border-blue-600 text-blue-600' : 'text-gray-700'
                }`}
              >
                <span className="text-xl">{item.icon}</span>
                <span className="font-medium">{item.name}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <header className="bg-white shadow-sm border-b border-gray-200 px-8 py-4">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-xl font-semibold text-gray-900 capitalize">
                  {currentView}
                </h2>
              </div>
              <div className="relative">
                <button
                  onClick={() => setShowProfileDropdown(!showProfileDropdown)}
                  className="flex items-center space-x-2 text-gray-700 hover:text-gray-900 focus:outline-none"
                >
                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                    <span className="text-white font-medium">👤</span>
                  </div>
                  <span className="font-medium">Profile</span>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                
                {showProfileDropdown && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-50">
                    <div className="py-1">
                      <button
                        onClick={() => {
                          setCurrentView('profile');
                          setShowProfileDropdown(false);
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      >
                        Manage Profile
                      </button>
                      <button
                        onClick={() => {
                          setCurrentView('dashboard');
                          setShowProfileDropdown(false);
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      >
                        Settings
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </header>

          {/* Content Area */}
          <main className="flex-1 p-8">
            {renderContent()}
          </main>
        </div>
      </div>
    </div>
  );
}

export default App;