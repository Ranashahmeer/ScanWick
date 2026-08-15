import { useRef, useState } from "react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/use-auth";
import { useUpdateProfile, useUploadAvatar } from "./profile-api";

function initialsFor(firstName: string | null, lastName: string | null, email: string): string {
  const fromName = [firstName, lastName].filter(Boolean).map((part) => part![0]).join("");
  if (fromName) return fromName.toUpperCase();
  return email.slice(0, 2).toUpperCase();
}

export function AccountTab() {
  const { user } = useAuth();
  const updateProfile = useUpdateProfile();
  const uploadAvatar = useUploadAvatar();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName, setLastName] = useState(user?.last_name ?? "");
  const [company, setCompany] = useState(user?.company ?? "");
  const [companySize, setCompanySize] = useState(user?.company_size ?? "");
  const [industry, setIndustry] = useState(user?.industry ?? "");
  const [primaryCurrency, setPrimaryCurrency] = useState(user?.primary_currency ?? "");
  const [language, setLanguage] = useState(user?.language ?? "");
  const [timezone, setTimezone] = useState(user?.timezone ?? "");

  function handleSave() {
    updateProfile.mutate(
      {
        first_name: firstName,
        last_name: lastName,
        company,
        company_size: companySize,
        industry,
        primary_currency: primaryCurrency,
        language,
        timezone,
      },
      {
        onSuccess: () => toast.success("Profile updated."),
        onError: (error) => toast.error(error instanceof Error ? error.message : "Could not save your changes."),
      }
    );
  }

  function handlePhotoClick() {
    fileInputRef.current?.click();
  }

  function handlePhotoChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    uploadAvatar.mutate(file, {
      onSuccess: () => toast.success("Photo updated."),
      onError: (error) => toast.error(error instanceof Error ? error.message : "Could not upload your photo."),
    });
  }

  return (
    <div className="acct-card">
      <h2>Profile</h2>

      <div className="acct-avatar-row">
        {user?.avatar_url ? (
          <img className="acct-avatar-large acct-avatar-img" src={user.avatar_url} alt="" />
        ) : (
          <span className="acct-avatar-large">
            {initialsFor(user?.first_name ?? null, user?.last_name ?? null, user?.email ?? "")}
          </span>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          hidden
          onChange={handlePhotoChange}
        />
        <button
          type="button"
          className="acct-btn-outline"
          onClick={handlePhotoClick}
          disabled={uploadAvatar.isPending}
        >
          {uploadAvatar.isPending ? "Uploading…" : "Change photo"}
        </button>
      </div>

      <div className="acct-form-grid">
        <label className="acct-field">
          <span>First name</span>
          <input type="text" value={firstName} onChange={(event) => setFirstName(event.target.value)} />
        </label>
        <label className="acct-field">
          <span>Last name</span>
          <input type="text" value={lastName} onChange={(event) => setLastName(event.target.value)} />
        </label>
        <label className="acct-field">
          <span>Email</span>
          <input type="email" value={user?.email ?? ""} disabled />
        </label>
        <label className="acct-field">
          <span>Company</span>
          <input type="text" value={company} onChange={(event) => setCompany(event.target.value)} />
        </label>
        <label className="acct-field">
          <span>Company size</span>
          <input type="text" value={companySize} onChange={(event) => setCompanySize(event.target.value)} />
        </label>
        <label className="acct-field">
          <span>Industry</span>
          <input type="text" value={industry} onChange={(event) => setIndustry(event.target.value)} />
        </label>
        <label className="acct-field">
          <span>Primary currency</span>
          <input
            type="text"
            value={primaryCurrency}
            onChange={(event) => setPrimaryCurrency(event.target.value)}
          />
        </label>
        <label className="acct-field">
          <span>Language</span>
          <input type="text" value={language} onChange={(event) => setLanguage(event.target.value)} />
        </label>
        <label className="acct-field">
          <span>Timezone</span>
          <input type="text" value={timezone} onChange={(event) => setTimezone(event.target.value)} />
        </label>
      </div>
      <button
        type="button"
        className="dqr-action-primary acct-mt"
        onClick={handleSave}
        disabled={updateProfile.isPending}
      >
        {updateProfile.isPending ? "Saving…" : "Save changes"}
      </button>
    </div>
  );
}
