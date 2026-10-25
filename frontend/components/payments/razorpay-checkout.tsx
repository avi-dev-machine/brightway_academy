"use client";

import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { paymentsApi } from "@/lib/api/payments";
import { receiptsApi } from "@/lib/api/receipts";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
import { toast } from "sonner";
import {
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Download,
  Loader2,
  CreditCard,
  QrCode,
  Smartphone,
  Copy,
  Check,
  Sparkles,
  ArrowRight,
  ExternalLink,
} from "lucide-react";
import type { CheckoutOrder, Fee, PaymentResult } from "@/types/api";

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => {
      open: () => void;
      on: (event: string, handler: (resp: unknown) => void) => void;
    };
  }
}

interface PaymentModalProps {
  fee: Fee | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RazorpayCheckoutModal({
  fee,
  open,
  onOpenChange,
}: PaymentModalProps) {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"upi" | "razorpay">("upi");
  const [checkoutOrder, setCheckoutOrder] = useState<CheckoutOrder | null>(null);
  const [verificationResult, setVerificationResult] = useState<PaymentResult | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [copiedVpa, setCopiedVpa] = useState(false);
  const [upiReference, setUpiReference] = useState("");

  const academyVpa = "brightwayacademy@icici";
  const upiAmount = fee ? (fee.balance_paise / 100).toFixed(2) : "0.00";
  const upiUri = fee
    ? `upi://pay?pa=${academyVpa}&pn=Brightway%20Computer%20Academy&am=${upiAmount}&cu=INR&tn=${encodeURIComponent(
        fee.title
      )}`
    : "";

  // 1. Direct UPI Confirmation Mutation
  const directUpiMutation = useMutation({
    mutationFn: (payload: { reference?: string; notes?: string }) => {
      if (!fee) throw new Error("No fee selected");
      return paymentsApi.submitUpiPayment(fee.id, payload);
    },
    onSuccess: (result) => {
      setVerificationResult(result);
      setVerifyError(null);
      toast.success("UPI payment recorded! Official receipt issued.");
      queryClient.invalidateQueries({ queryKey: ["student-fees"] });
      queryClient.invalidateQueries({ queryKey: ["student-receipts"] });
      queryClient.invalidateQueries({ queryKey: ["student-fee-summary"] });
      queryClient.invalidateQueries({ queryKey: ["student-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["student-me"] });
    },
    onError: () => {
      toast.error("Failed to record UPI payment. Please try again or contact administration.");
    },
  });

  // 2. Razorpay Order Creation Mutation
  const createOrderMutation = useMutation({
    mutationFn: (targetFee: Fee) =>
      paymentsApi.createOrder({ fee_id: targetFee.id }),
    onSuccess: (order) => {
      setCheckoutOrder(order);
      setVerificationResult(null);
      setVerifyError(null);
      launchRazorpay(order);
    },
    onError: () => {
      toast.error("Unable to initiate Razorpay order. Please try again.");
    },
  });

  // 3. Launch Razorpay script
  const launchRazorpay = (order: CheckoutOrder) => {
    const initRazorpay = () => {
      if (!window.Razorpay) {
        toast.error("Razorpay SDK failed to load. Please check internet connection.");
        return;
      }
      try {
        const options: Record<string, unknown> = {
          key: order.key_id,
          amount: order.amount_paise,
          currency: order.currency,
          name: "Brightway Computer Academy",
          description: order.fee_title,
          order_id: order.provider_order_id,
          prefill: {
            name: order.student_name,
            contact: order.contact || undefined,
          },
          theme: {
            color: "#059669",
          },
          handler: async (response: {
            razorpay_order_id: string;
            razorpay_payment_id: string;
            razorpay_signature: string;
          }) => {
            await submitVerification({
              provider_order_id: response.razorpay_order_id,
              provider_payment_id: response.razorpay_payment_id,
              signature: response.razorpay_signature,
            });
          },
          modal: {
            ondismiss: () => {
              console.info("Razorpay checkout closed");
            },
          },
        };

        const rzp = new window.Razorpay(options);
        rzp.open();
      } catch (err) {
        console.error("Error opening Razorpay:", err);
        toast.error("Unable to open Razorpay checkout.");
      }
    };

    if (typeof window !== "undefined" && window.Razorpay) {
      initRazorpay();
    } else {
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = initRazorpay;
      script.onerror = () => toast.error("Failed to load Razorpay SDK from checkout.razorpay.com");
      document.body.appendChild(script);
    }
  };

  // 4. Razorpay Verification
  const submitVerification = async (verifyPayload: {
    provider_order_id: string;
    provider_payment_id: string;
    signature: string;
  }) => {
    setIsVerifying(true);
    setVerifyError(null);
    try {
      const result = await paymentsApi.verify(verifyPayload);
      setVerificationResult(result);

      if (result.outcome === "SUCCEEDED" || result.outcome === "ALREADY_PROCESSED") {
        toast.success("Payment verified! Official receipt issued.");
      } else if (result.outcome === "PENDING") {
        toast.info("Your payment is currently being verified. Please check history shortly.");
      } else {
        toast.error(`Payment state: ${result.outcome}`);
      }

      queryClient.invalidateQueries({ queryKey: ["student-fees"] });
      queryClient.invalidateQueries({ queryKey: ["student-receipts"] });
      queryClient.invalidateQueries({ queryKey: ["student-fee-summary"] });
      queryClient.invalidateQueries({ queryKey: ["student-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["student-me"] });
    } catch {
      setVerifyError("Verification failed on server. Please contact academy administration.");
      toast.error("Payment verification failed on server.");
    } finally {
      setIsVerifying(false);
    }
  };

  const copyVpa = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedVpa(true);
    toast.success(`Copied UPI ID '${text}' to clipboard!`);
    setTimeout(() => setCopiedVpa(false), 2500);
  };

  const resetModal = () => {
    setCheckoutOrder(null);
    setVerificationResult(null);
    setVerifyError(null);
    setUpiReference("");
    setActiveTab("upi");
    onOpenChange(false);
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) resetModal();
      }}
    >
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base text-slate-900">
            <Smartphone className="h-5 w-5 text-emerald-600" />
            Online Fee Payment & UPI
          </DialogTitle>
        </DialogHeader>

        {fee && (
          <div className="space-y-4 pt-1">
            {/* Fee Overview Card */}
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                Fee Details
              </span>
              <p className="text-sm font-bold text-slate-900 mt-0.5">{fee.title}</p>
              <div className="mt-2.5 flex items-baseline justify-between border-t border-slate-200/80 pt-2">
                <span className="text-xs text-slate-500 font-medium">Payable Balance:</span>
                <span className="text-2xl font-black text-emerald-600">
                  {formatCurrency(fee.balance_paise)}
                </span>
              </div>
            </div>

            {/* Verifying Spinner */}
            {(isVerifying || directUpiMutation.isPending) && (
              <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-6 text-center animate-pulse">
                <Loader2 className="mx-auto h-8 w-8 animate-spin text-emerald-600 mb-2" />
                <p className="text-xs font-semibold text-emerald-950">
                  Confirming payment & issuing digital receipt...
                </p>
                <p className="text-[11px] text-emerald-700 mt-1">
                  Synchronizing tuition ledger and updating monthly dues.
                </p>
              </div>
            )}

            {/* Success Card with PDF Download */}
            {verificationResult && (
              <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-5 text-center animate-fade-in">
                <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-600 mb-2" />
                <h4 className="text-base font-bold text-slate-900">Payment Successfully Recorded!</h4>
                <p className="text-xs text-slate-600 mt-1">
                  Your tuition payment has been officially recorded and credited to your account.
                </p>

                {verificationResult.receipt && (
                  <div className="mt-4 p-3 bg-white rounded-lg border border-emerald-200 text-left text-xs space-y-1.5 shadow-2xs">
                    <div className="flex justify-between py-0.5">
                      <span className="text-slate-500">Receipt No:</span>
                      <span className="font-mono font-bold text-emerald-700">
                        {verificationResult.receipt.receipt_number}
                      </span>
                    </div>
                    <div className="flex justify-between py-0.5">
                      <span className="text-slate-500">Amount Paid:</span>
                      <span className="font-bold text-slate-900">
                        {formatCurrency(verificationResult.receipt.amount_paise)}
                      </span>
                    </div>
                    <div className="flex justify-between py-0.5">
                      <span className="text-slate-500">Method:</span>
                      <span className="font-semibold text-emerald-800">
                        UPI / Online Settlement
                      </span>
                    </div>
                    <div className="mt-3 pt-2 border-t border-slate-100 flex justify-end">
                      <a
                        href={receiptsApi.downloadUrl(verificationResult.receipt.id)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 text-xs gap-1.5 border-emerald-300 text-emerald-800 hover:bg-emerald-50 font-semibold"
                        >
                          <Download className="h-3.5 w-3.5 text-emerald-700" />
                          Download Official PDF Receipt
                        </Button>
                      </a>
                    </div>
                  </div>
                )}

                <Button
                  variant="primary"
                  size="sm"
                  className="mt-4 w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
                  onClick={resetModal}
                >
                  Done
                </Button>
              </div>
            )}

            {/* Error Message */}
            {verifyError && (
              <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-center">
                <AlertCircle className="mx-auto h-6 w-6 text-rose-600 mb-1" />
                <p className="text-xs font-semibold text-rose-900">{verifyError}</p>
              </div>
            )}

            {/* Main Tabs (when not verified and not loading) */}
            {!verificationResult && !isVerifying && !directUpiMutation.isPending && (
              <div className="space-y-4">
                {/* Method Switcher Buttons */}
                <div className="grid grid-cols-2 gap-2 p-1 bg-slate-100 rounded-lg">
                  <button
                    type="button"
                    onClick={() => setActiveTab("upi")}
                    className={`py-2 text-xs font-bold rounded-md transition-all flex items-center justify-center gap-1.5 ${
                      activeTab === "upi"
                        ? "bg-white text-emerald-700 shadow-xs"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    <QrCode className="h-3.5 w-3.5" />
                    UPI & QR Code (Direct)
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab("razorpay")}
                    className={`py-2 text-xs font-bold rounded-md transition-all flex items-center justify-center gap-1.5 ${
                      activeTab === "razorpay"
                        ? "bg-white text-blue-700 shadow-xs"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    <CreditCard className="h-3.5 w-3.5" />
                    Cards & NetBanking
                  </button>
                </div>

                {/* TAB 1: UPI & DYNAMIC QR CODE */}
                {activeTab === "upi" && (
                  <div className="rounded-xl border-2 border-emerald-500/40 bg-gradient-to-br from-emerald-50/70 via-white to-emerald-50/30 p-4 text-center space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 uppercase tracking-wide">
                        <Sparkles className="h-3 w-3" />
                        Zero Extra Charges • Instant Settlement
                      </span>
                      <span className="text-[11px] font-semibold text-emerald-800">
                        ₹{upiAmount}
                      </span>
                    </div>

                    {/* QR Code Container */}
                    <div className="flex flex-col items-center justify-center pt-1">
                      <div className="p-3 bg-white rounded-2xl border border-slate-200 shadow-sm inline-block">
                        <QRCodeSVG
                          value={upiUri}
                          size={160}
                          level="M"
                          includeMargin={false}
                        />
                      </div>
                      <p className="text-[11px] font-semibold text-slate-700 mt-2">
                        Scan with any UPI App to Pay
                      </p>
                    </div>

                    {/* UPI Brand Badges */}
                    <div className="flex items-center justify-center gap-1.5 flex-wrap">
                      {["Google Pay", "PhonePe", "Paytm", "BHIM UPI", "CRED"].map((app) => (
                        <span
                          key={app}
                          className="px-2 py-0.5 rounded bg-white border border-slate-200 text-[10px] font-medium text-slate-700 shadow-2xs"
                        >
                          {app}
                        </span>
                      ))}
                    </div>

                    {/* Academy UPI ID Box */}
                    <div className="rounded-lg bg-white border border-emerald-200 p-2.5 flex items-center justify-between text-left text-xs">
                      <div>
                        <span className="text-[10px] text-slate-400 block font-medium">
                          Academy UPI ID
                        </span>
                        <span className="font-mono font-bold text-emerald-800">
                          {academyVpa}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => copyVpa(academyVpa)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-50 hover:bg-emerald-100 text-[11px] font-medium text-emerald-700 border border-emerald-200 transition-colors"
                      >
                        {copiedVpa ? (
                          <>
                            <Check className="h-3.5 w-3.5 text-emerald-600" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5" />
                            Copy
                          </>
                        )}
                      </button>
                    </div>

                    {/* Mobile UPI Intent Button */}
                    <div className="block sm:hidden">
                      <a href={upiUri} className="block w-full">
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full text-xs font-bold gap-1.5 border-emerald-300 text-emerald-800 hover:bg-emerald-50"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                          Open UPI App on this Phone
                        </Button>
                      </a>
                    </div>

                    {/* Confirmation Section */}
                    <div className="pt-2 border-t border-emerald-100 space-y-2 text-left">
                      <label className="text-[11px] font-semibold text-slate-700 block">
                        UPI Transaction ID / UTR (Optional):
                      </label>
                      <input
                        type="text"
                        value={upiReference}
                        onChange={(e) => setUpiReference(e.target.value)}
                        placeholder="e.g. 12-digit UPI UTR from Google Pay / PhonePe"
                        className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
                      />

                      <Button
                        variant="primary"
                        size="sm"
                        className="w-full text-xs font-bold gap-2 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm mt-1"
                        onClick={() =>
                          directUpiMutation.mutate({
                            reference: upiReference.trim() || undefined,
                          })
                        }
                      >
                        <CheckCircle2 className="h-4 w-4" />
                        I Have Paid ₹{upiAmount} via UPI (Verify & Get Receipt)
                      </Button>
                    </div>
                  </div>
                )}

                {/* TAB 2: RAZORPAY GATEWAY */}
                {activeTab === "razorpay" && (
                  <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-4 text-center space-y-3">
                    <div className="flex items-center justify-center gap-1.5 text-xs font-bold text-blue-900">
                      <CreditCard className="h-4 w-4 text-blue-600" />
                      <span>Razorpay Live Test Gateway</span>
                    </div>

                    <p className="text-xs text-slate-600">
                      Pay using Credit Card, Debit Card (Visa, Mastercard, RuPay), or NetBanking across 50+ Indian banks.
                    </p>

                    <div className="rounded-lg bg-white p-3 border border-slate-200 text-left text-xs space-y-1">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Payment Gateway:</span>
                        <span className="font-medium text-slate-800">Razorpay (Test Mode)</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Payable Amount:</span>
                        <span className="font-bold text-blue-700">{formatCurrency(fee.balance_paise)}</span>
                      </div>
                    </div>

                    <Button
                      variant="primary"
                      size="sm"
                      className="w-full text-xs font-bold gap-2 py-2.5 bg-blue-600 hover:bg-blue-700 text-white"
                      disabled={createOrderMutation.isPending}
                      onClick={() => {
                        if (checkoutOrder) {
                          launchRazorpay(checkoutOrder);
                        } else {
                          createOrderMutation.mutate(fee);
                        }
                      }}
                    >
                      {createOrderMutation.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Initializing Razorpay...
                        </>
                      ) : (
                        <>
                          <CreditCard className="h-4 w-4" />
                          Open Razorpay Checkout
                          <ArrowRight className="h-3.5 w-3.5" />
                        </>
                      )}
                    </Button>

                    <p className="text-[10px] text-slate-400">
                      Supports Cards, Netbanking & Wallets with instant digital authorization.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Bottom Security Assurance */}
            <div className="flex items-center justify-center gap-1.5 text-[11px] text-slate-400 pt-1">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
              100% Encrypted & Authenticated Transaction
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
