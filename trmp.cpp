using namespace std;
#include <string>
#include<stdio.h>
#include<stdlib.h>
#include<map>
#include<vector>

class Solution {
public:
    map<char,pair<int,int>>direction = {{'N', make_pair(0,-1)},{'S', make_pair(0,1)},{'W', make_pair(1,0)},{'E', make_pair(-1,0)}};
    vector<char>list = {'N','S','E','W'};

    int helperFunction(string s,int k,int x,int y, int i){
        if (i == s.length())
            return abs(x) + abs(y);
        
        int tempResult = 0;
        for (int i = 0; i < 4; i++)
        {
            pair<int,int> temp = direction[s[i]];
            if (list[i] == s[i])
            {
                tempResult = max(tempResult,helperFunction(s,k,x + temp.first,y + temp.second,i+1));
            }else{
                if (k > 0)
                {
                    tempResult = max(tempResult,helperFunction(s,k-1,x + temp.first,y + temp.second,i+1));
                }
            }
        }
        return max(tempResult,abs(x)+abs(y));
    }

    int maxDistance(string s, int k) {
        return helperFunction(s,k,0,0,0);
    }
};

Solution S;
string s = "NWSE";
int k = 1;
int result = S.maxDistance(s,k);