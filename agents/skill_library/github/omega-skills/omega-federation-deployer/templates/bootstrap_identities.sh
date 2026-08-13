#!/bin/bash
# OMEGA Identity Bootstrapper
mkdir -p ~/omega_root/bin ~/omega_root/profiles ~/omega_root/logs

cat > ~/omega_root/bin/tp-switch << 'EOS'
#!/bin/bash
PROFILE=$2
case "$1" in
    create) mkdir -p ~/omega_root/profiles/$PROFILE; echo "Profile $PROFILE created." ;;
    activate) echo "$PROFILE" > ~/omega_root/profiles/.current; echo "Profile $PROFILE activated." ;;
esac
EOS
chmod +x ~/omega_root/bin/tp-switch

~/omega_root/bin/tp-switch create angel-engine
~/omega_root/bin/tp-switch create will-engine
~/omega_root/bin/tp-switch create investigator
~/omega_root/bin/tp-switch activate angel-engine
