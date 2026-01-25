#!/bin/bash
echo "🚀 NICE v4 PRO 배포 도우미"
echo "--------------------------------------"
echo "Render 웹사이트는: https://nice-v4-pro.onrender.com 입니다."
echo "이 사이트에 코드를 올리려면 GitHub 저장소(Repository) 주소가 필요합니다."
echo ""
echo "예시: https://github.com/my-username/nice-v4-pro.git"
echo "--------------------------------------"

read -p "GitHub 저장소 주소를 입력하세요: " REPO_URL

if [ -z "$REPO_URL" ]; then
    echo "❌ 주소가 입력되지 않았습니다. 다시 실행해주세요."
    exit 1
fi

echo ""
echo "🔗 원격 저장소 연결 중: $REPO_URL"
git remote remove origin 2>/dev/null
git remote add origin "$REPO_URL"

echo "📤 GitHub로 코드 푸시 (배포 시작)..."
# 강제 푸시는 주의해야 하지만, 초기 세팅이므로 force 사용
git push -u origin main --force

echo ""
echo "✅ 푸시가 완료되었습니다!"
echo "이제 Render 대시보드에서 배포가 시작되었는지 확인하세요."
