#include <iostream>
#include <vector>


using namespace std;

int recur(vector<int>& array, vector<vector<int> >&dp){
    int maxVal = max(array.begin(), array.end());
    for(int i = 1; i < array.size();i++){
        //Check previous adjacent

        if(array[i] == array[i - 1]){
            int recResult;
            if(dp[i - 1][i]){
                recResult = dp[i - 1][i];
            }else{
                int firstVal = array[i - 1];
                int secondVal = array[i];
                vector<int> copyOfVector = array;
                copyOfVector.erase(array.begin()+i);
                copyOfVector[i - 1] = firstVal + secondVal;
                recResult = recur(copyOfVector);
                dp[i - 1[i]] = recResult;
            }
            if(maxVal < recResult){
                maxVal = recResult;
            }
        }if(i - 2 >= 0 && array[i] == array[i - 2]){
            int recResult;
            if(dp[i - 2][i]){
                recResult = dp[i - 2][i];
            }else{
                int firstVal = array[i - 2];
                int secondVal = array[i - 1];
                int thirdVal = array[i];
                vector<int> copyOfVector = array;
                copyOfVector.erase(array.begin()+i);
                copyOfVector.erase(array.begin()+i - 1);
                copyOfVector[i - 2] = firstVal + secondVal + thirdVal;
                recResult = recur(copyOfVector);
                dp[i - 2[i]] = recResult;
            }
            if(maxVal < recResult){
                maxVal = recResult;
            }
        }
    }
    return maxVal;
}

int main() {
    int N;
    cin >> N;

    vector<vector<int> > dp(N, vector<int>(N, -1));
    vector<int> startArray(N);

    for(int i = 0; i < N; i++){
        cin >> startArray[i];
    }


}








