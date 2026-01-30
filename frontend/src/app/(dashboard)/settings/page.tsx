"use client";

import { useState } from "react";
import { toast } from "sonner";
import * as api from "@/lib/api-client";
import { useAuth } from "@/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Shield, ShieldOff, User } from "lucide-react";
import { formatDateTime } from "@/lib/utils";
import type { TOTPSetupResponse } from "@/types/api";

export default function SettingsPage() {
  const { user } = useAuth();

  const [totpSetup, setTotpSetup] = useState<TOTPSetupResponse | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [is2FAEnabled, setIs2FAEnabled] = useState<boolean | null>(null);
  const [isSettingUp, setIsSettingUp] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isDisabling, setIsDisabling] = useState(false);
  const [showDisable, setShowDisable] = useState(false);

  const handleSetup2FA = async () => {
    setIsSettingUp(true);
    try {
      const result = await api.setup2FA();
      setTotpSetup(result);
      setIs2FAEnabled(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Setup failed";
      if (msg.includes("already enabled")) {
        setIs2FAEnabled(true);
        toast.info("2FA is already enabled on your account");
      } else {
        toast.error(msg);
      }
    } finally {
      setIsSettingUp(false);
    }
  };

  const handleVerify2FA = async () => {
    if (!totpCode.trim()) return;
    setIsVerifying(true);
    try {
      await api.verify2FA(totpCode.trim());
      toast.success("2FA enabled successfully");
      setIs2FAEnabled(true);
      setTotpSetup(null);
      setTotpCode("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setIsVerifying(false);
    }
  };

  const handleDisable2FA = async () => {
    if (!disableCode.trim()) return;
    setIsDisabling(true);
    try {
      await api.disable2FA(disableCode.trim());
      toast.success("2FA disabled");
      setIs2FAEnabled(false);
      setShowDisable(false);
      setDisableCode("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to disable 2FA");
    } finally {
      setIsDisabling(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Email</p>
              <p className="font-medium">{user?.email}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Full Name</p>
              <p className="font-medium">{user?.full_name || "-"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Status</p>
              <p className="font-medium">{user?.is_active ? "Active" : "Inactive"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Member Since</p>
              <p className="font-medium">
                {user?.created_at ? formatDateTime(user.created_at) : "-"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Two-Factor Authentication
          </CardTitle>
          <CardDescription>
            Add an extra layer of security to your account using a TOTP authenticator app.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {is2FAEnabled === true && !showDisable && (
            <>
              <Alert>
                <Shield className="h-4 w-4" />
                <AlertDescription>
                  Two-factor authentication is enabled on your account.
                </AlertDescription>
              </Alert>
              <Button
                variant="outline"
                onClick={() => setShowDisable(true)}
                className="text-destructive"
              >
                <ShieldOff className="mr-2 h-4 w-4" />
                Disable 2FA
              </Button>
            </>
          )}

          {showDisable && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Enter your current 2FA code to disable two-factor authentication.
              </p>
              <div className="flex gap-2">
                <Input
                  value={disableCode}
                  onChange={(e) => setDisableCode(e.target.value)}
                  placeholder="123456"
                  maxLength={6}
                  className="w-32"
                />
                <Button onClick={handleDisable2FA} disabled={isDisabling} variant="destructive">
                  {isDisabling && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Confirm Disable
                </Button>
                <Button variant="outline" onClick={() => setShowDisable(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {is2FAEnabled !== true && !totpSetup && (
            <Button onClick={handleSetup2FA} disabled={isSettingUp}>
              {isSettingUp && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              <Shield className="mr-2 h-4 w-4" />
              Setup 2FA
            </Button>
          )}

          {totpSetup && (
            <div className="space-y-4">
              <Separator />
              <p className="text-sm text-muted-foreground">
                Scan the QR code below with your authenticator app (Google Authenticator,
                Authy, etc.), then enter the 6-digit code to verify.
              </p>

              {totpSetup.qr_code_base64 && (
                <div className="flex justify-center">
                  <img
                    src={`data:image/png;base64,${totpSetup.qr_code_base64}`}
                    alt="2FA QR Code"
                    className="w-48 h-48 border rounded"
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">
                  Manual entry key:
                </Label>
                <code className="block text-sm bg-muted p-2 rounded font-mono break-all">
                  {totpSetup.secret}
                </code>
              </div>

              <div className="flex gap-2 items-end">
                <div className="space-y-2">
                  <Label htmlFor="totp-verify">Verification Code</Label>
                  <Input
                    id="totp-verify"
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value)}
                    placeholder="123456"
                    maxLength={6}
                    className="w-32"
                  />
                </div>
                <Button onClick={handleVerify2FA} disabled={isVerifying || !totpCode.trim()}>
                  {isVerifying && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Verify & Enable
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
